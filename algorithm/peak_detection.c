
void accel_action_inference_thread_func(void *a, void *b, void *c)
{
    ffh_event_t peak;
    struct acc_inference_result result;
    uint64_t inference_time;
    ffh_candidate_msg_t cand;

    struct k_poll_event events[2] = {
        K_POLL_EVENT_STATIC_INITIALIZER(
            K_POLL_TYPE_MSGQ_DATA_AVAILABLE,
            K_POLL_MODE_NOTIFY_ONLY,
            &ffh_pressure_msgq,
            0),

        K_POLL_EVENT_STATIC_INITIALIZER(
            K_POLL_TYPE_MSGQ_DATA_AVAILABLE,
            K_POLL_MODE_NOTIFY_ONLY,
            &ffh_candidate_msgq,
            0),
    };

    while (1)
    {

        k_poll(events, 2, K_FOREVER);

        if (events[0].state == K_POLL_STATE_MSGQ_DATA_AVAILABLE)
        {
            ffh_pressure_msg_t pmsg;

            while (k_msgq_get(&ffh_pressure_msgq, &pmsg, K_NO_WAIT) == 0)
            {
                pressure_hist_push(&pmsg);

#if Function_Check_Print > 0
                printk("[FFH_PRESS] ts=%llu, pressure_ukpa=%lld\n",
                       pmsg.ts_ms,
                       pmsg.pressure_ukpa);
#endif
            }


            try_process_pending_candidates();

            events[0].state = K_POLL_STATE_NOT_READY;
        }


        if (events[1].state == K_POLL_STATE_MSGQ_DATA_AVAILABLE)
        {
            ffh_candidate_msg_t cand;

            while (k_msgq_get(&ffh_candidate_msgq, &cand, K_NO_WAIT) == 0)
            {

                if (!process_ffh_candidate_if_ready(&cand))
                {
                    register_infer_pending(&cand);

#if Function_Check_Print > 0
                    printk("[FFH] candidate pending | idx=%u ts=%llu pre=%u gap=%u stable=%u\n",
                           cand.peak_index,
                           cand.peak_ts_ms,
                           cand.pre_peak_found,
                           cand.pre_peak_gap,
                           cand.stable_count);
#endif
                }
            }

            events[1].state = K_POLL_STATE_NOT_READY;
        }
    } // end while(1)
} // end accel_action_inference_thread_func

static void register_infer_pending(const ffh_candidate_msg_t *cand)
{
    for (int i = 0; i < FFH_INFER_PENDING_MAX; i++)
    {
        if (!ffh_infer_pending[i].used)
        {
            ffh_infer_pending[i].used = 1;
            ffh_infer_pending[i].cand = *cand;
            ffh_infer_pending[i].queued_ts_ms = k_uptime_get();
            return;
        }
    }

    printk("[FFH] infer pending full\n");
}

static void try_process_pending_candidates(void)
{
    uint64_t now_ms = k_uptime_get();

    for (int i = 0; i < FFH_INFER_PENDING_MAX; i++)
    {
        if (!ffh_infer_pending[i].used)
            continue;

        if ((now_ms - ffh_infer_pending[i].queued_ts_ms) > FFH_INFER_PENDING_TIMEOUT_MS)
        {
            printk("[FFH] pending timeout | idx=%u ts=%llu\n",
                   ffh_infer_pending[i].cand.peak_index,
                   ffh_infer_pending[i].cand.peak_ts_ms);

            ffh_infer_pending[i].used = 0;
            continue;
        }

        if (process_ffh_candidate_if_ready(&ffh_infer_pending[i].cand))
        {
            ffh_infer_pending[i].used = 0;
        }
    }
}

static bool process_ffh_candidate_if_ready(const ffh_candidate_msg_t *cand)
{
    ffh_pressure_msg_t prev_msg = {0}, curr_msg = {0}, next_msg = {0};

    if (!pressure_hist_get_triplet(cand->peak_ts_ms, &prev_msg, &curr_msg, &next_msg))
    {
        return false;
    }

    uint64_t detect_ts_ms = k_uptime_get();

    int64_t pressure_delta_ukpa = next_msg.pressure_ukpa - prev_msg.pressure_ukpa;
    if (pressure_delta_ukpa < 0)
        pressure_delta_ukpa = -pressure_delta_ukpa;

    uint8_t cond5_pass = (pressure_delta_ukpa >= FFH_PRESSURE_DELTA_THRESH_UKPA) ? 1 : 0;

    uint32_t score = ffh_calculate_score(cand, cond5_pass, pressure_delta_ukpa);
    uint8_t detected = ffh_is_detected(cand, score);

    ffh_result_t result = {0};
    result.detected = detected;
    result.score = score;

    result.pre_peak_found = cand->pre_peak_found;
    result.pre_peak_gap = cand->pre_peak_gap;
    result.stable_count = cand->stable_count;

    result.cond5_pass = cond5_pass;
    result.pressure_delta_ukpa = pressure_delta_ukpa;

    result.peak_ts_ms = cand->peak_ts_ms;
    result.detect_ts_ms = detect_ts_ms;
    result.latency_ms = detect_ts_ms - cand->peak_ts_ms;

    result.peak_mag_ms2_q16 = cand->peak_mag_ms2_q16;
    result.peak_amp_ms2_q16 = cand->peak_amp_ms2_q16;

#if Function_Check_Print > 0
    printk("[FFH] idx=%u ts=%llu pre=%u gap=%u stable=%u cond5=%u dp=%lld score=%u detect=%u latency=%llu\n",
           cand->peak_index,
           cand->peak_ts_ms,
           cand->pre_peak_found,
           cand->pre_peak_gap,
           cand->stable_count,
           cond5_pass,
           pressure_delta_ukpa,
           score,
           detected,
           result.latency_ms);
#endif

    if (k_msgq_put(&ffh_result_msgq, &result, K_NO_WAIT) != 0)
    {
        printk("[FFH] ffh_result_msgq full\n");
    }

    return true;
}
static bool pressure_hist_get_triplet(
    uint64_t target_ts_ms,
    ffh_pressure_msg_t *out_prev,
    ffh_pressure_msg_t *out_curr,
    ffh_pressure_msg_t *out_next)
{
    if (pressure_hist_count < 3)
        return false;

    int curr_idx = -1;
    if (!pressure_hist_find_nearest_index(target_ts_ms, &curr_idx))
        return false;

    // ring buffer 상에서 curr의 앞/뒤 인덱스
    int prev_idx = (curr_idx + FFH_PRESSURE_HISTORY_SIZE - 1) % FFH_PRESSURE_HISTORY_SIZE;
    int next_idx = (curr_idx + 1) % FFH_PRESSURE_HISTORY_SIZE;

    // 하지만 원형 배열 특성상 prev/next 위치가 실제 유효 데이터가 아닐 수도 있으므로
    // 최소한 timestamp 순서가 맞는지 확인
    uint64_t prev_ts = pressure_hist[prev_idx].ts_ms;
    uint64_t curr_ts = pressure_hist[curr_idx].ts_ms;
    uint64_t next_ts = pressure_hist[next_idx].ts_ms;

    if (!(prev_ts < curr_ts && curr_ts < next_ts))
    {
        return false;
    }

    *out_prev = pressure_hist[prev_idx];
    *out_curr = pressure_hist[curr_idx];
    *out_next = pressure_hist[next_idx];

    return true;
}

static bool pressure_hist_find_nearest_index(
    uint64_t target_ts_ms,
    int *out_idx)
{
    if (pressure_hist_count == 0)
        return false;

    uint64_t best_diff = UINT64_MAX;
    int best_idx = -1;

    for (int i = 0; i < pressure_hist_count; i++)
    {
        int idx = (pressure_hist_head + FFH_PRESSURE_HISTORY_SIZE - 1 - i) % FFH_PRESSURE_HISTORY_SIZE;

        uint64_t ts = pressure_hist[idx].ts_ms;
        uint64_t diff = (ts > target_ts_ms) ? (ts - target_ts_ms)
                                            : (target_ts_ms - ts);

        if (diff < best_diff)
        {
            best_diff = diff;
            best_idx = idx;
        }
    }

    if (best_idx < 0)
        return false;

    *out_idx = best_idx;
    return true;
} // end static bool pressure_hist_find_nearest_index

static uint32_t ffh_calculate_score(
    const ffh_candidate_msg_t *cand,
    bool cond5_pass,
    int64_t pressure_delta_ukpa)
{
    uint32_t score = 0;

    // 1) pre-peak
    if (cand->pre_peak_found)
    {
        if (cand->pre_peak_gap <= 10)
            score += 20;
        else if (cand->pre_peak_gap <= 20)
            score += 15;
        else if (cand->pre_peak_gap <= 40)
            score += 10;
    }

    // 2) stable count
    if (cand->stable_count >= 5)
        score += 35;
    else if (cand->stable_count >= 4)
        score += 30;
    else if (cand->stable_count >= 3)
        score += 20;

    // 3) pressure
    if (cond5_pass)
    {
        if (pressure_delta_ukpa >= 20000LL) // 0.20 hPa
            score += 40;
        else if (pressure_delta_ukpa >= 12000LL) // 0.12 hPa
            score += 30;
    }

    // 4) peak magnitude 보강
    if (cand->peak_mag_ms2_q16 >= TO_Q16(6.0f * GRAVITY_MS2))
        score += 10;

    // 5) peak amplitude 보강
    if (cand->peak_amp_ms2_q16 >= TO_Q16(1.5f * GRAVITY_MS2))
        score += 10;

    // if (score > 100)
//        score = 100;

    return score;
}
static bool ffh_is_detected(
    const ffh_candidate_msg_t *cand,
    uint32_t score)
{
    return (score >= 60 && cand->stable_count >= 3);
}

static bool ffh_is_detected(
    const ffh_candidate_msg_t *cand,
    uint32_t score)
{
    return (score >= 60 && cand->stable_count >= 3);
}

static bool ffh_get_pressure_window(
    uint64_t peak_ts_ms,
    int64_t *out_before_ukpa,
    int64_t *out_after_ukpa)
{
    bool ok_before = pressure_hist_find_nearest(peak_ts_ms - 1000, out_before_ukpa);
    bool ok_after = pressure_hist_find_nearest(peak_ts_ms + 1000, out_after_ukpa);

    return (ok_before && ok_after);
}
