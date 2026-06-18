

#include <zephyr/kernel.h>
#include <stdint.h>
#include <string.h>
#include <limits.h>

#include "accelerometer.h"
#include "accel_data_processing.h"
#include "accelerometer_sdcard.h"

#include "accel_ble.h"
#include "accel_action_inference.h"

static struct k_thread accel_data_processing_thread_data;
#define ACCEL_CONSUMER_THREAD_STACK_SIZE 4096

#define ENABLE_LED 0
#define Function_Check_Print 0
#define RECORD_DETECTED_PEAK_TIME 0
#define FFH_INFERENCE 1

#define PEAK_MIN_AMP_Q16            ((int32_t)(0.05 * (1<<16)))
#define MIN_PEAK_INTERVAL_MS        100
#define WIN_L                       5   
#define WIN_R                       5   
#define WIN_N                       (WIN_L + 1 + WIN_R) 

#define PEAK_MAG_THRESH_G           1.30f   
#define PEAK_MAG_THRESH_MS2         PEAK_MAG_THRESH_G * GRAVITY_MS2
#define PEAK_MAG_THRESH_MS2_Q16     TO_Q16(PEAK_MAG_THRESH_MS2)
#define PEAK_MAG2_THRESH_MS2_Q32    ((int64_t)PEAK_MAG_THRESH_MS2_Q16 * PEAK_MAG_THRESH_MS2_Q16)

#define AVG_MAG_THRESH_G            1.10f   
#define AVG_MAG_THRESH_MS2          AVG_MAG_THRESH_G * GRAVITY_MS2
#define AVG_MAG_THRESH_MS2_Q16      TO_Q16(AVG_MAG_THRESH_MS2)
#define AVG_MAG2_THRESH_MS2_Q32     ((int64_t)AVG_MAG_THRESH_MS2_Q16 * AVG_MAG_THRESH_MS2_Q16)

#define PEAK_AVG_MAG_THRESH_G       1.20f   
#define PEAK_AVG_MAG_THRESH_MS2     PEAK_AVG_MAG_THRESH_G * GRAVITY_MS2
#define PEAK_AVG_MAG_THRESH_MS2_Q16 TO_Q16(PEAK_AVG_MAG_THRESH_MS2)

#define Q16_PARAMETRE               65536.0
#define Q32_PARAMETRE               Q16_PARAMETRE * Q16_PARAMETRE

#define FFH_MAG_THRESH_G            5.0f
#define FFH_MAG_THRESH_MS2          (FFH_MAG_THRESH_G * GRAVITY_MS2)
#define FFH_MAG_THRESH_Q16          TO_Q16(FFH_MAG_THRESH_MS2)

#define FFH_AMP_THRESH_G            1.0f
#define FFH_AMP_THRESH_MS2          (FFH_AMP_THRESH_G * GRAVITY_MS2)
#define FFH_AMP_THRESH_Q16          TO_Q16(FFH_AMP_THRESH_MS2)

#define STABLE_LOW_G                0.85f
#define STABLE_HIGH_G               1.20f
#define STABLE_LOW_MS2              (STABLE_LOW_G * GRAVITY_MS2)
#define STABLE_HIGH_MS2             (STABLE_HIGH_G * GRAVITY_MS2)
#define STABLE_LOW_Q16              TO_Q16(STABLE_LOW_MS2)
#define STABLE_HIGH_Q16             TO_Q16(STABLE_HIGH_MS2)

#define MAX_PENDING_FFH             8

static uint8_t peak_hist_head = 0;
static uint8_t peak_hist_count = 0;
static ffh_pending_candidate_t ffh_pending[MAX_PENDING_FFH];
K_MSGQ_DEFINE(ffh_candidate_msgq, sizeof(ffh_candidate_msg_t), 8, 4);
static bool ffh_check_cond3_with_prev_peak(
    const prev_peak_info_t *prev_peak,
    uint32_t current_index,
    int32_t current_mag_ms2_q16,
    int32_t current_amp_ms2_q16,
    uint32_t *out_gap);
static void update_pending_candidates_with_sample(
    uint32_t current_sample_index,
    int32_t current_mag_ms2_q16);

K_THREAD_STACK_DEFINE(accel_data_processing_thread_stack, ACCEL_CONSUMER_THREAD_STACK_SIZE);

K_MSGQ_DEFINE(accel_sd_msgq, sizeof(sdcard_accel_data), 400, 4); 

#if RECORD_DETECTED_PEAK_TIME > 0
K_MSGQ_DEFINE(detected_time_msgq, sizeof(detected_peak_t), 100 , 4); 
#endif
int init_thread_accel_data_processing(void)
{
    int ret = 0;
#if Function_Check_Print > 0
    printk("Start to Acc Data Processing Thread Function\n");
#endif
    k_thread_create(&accel_data_processing_thread_data,                        
                    accel_data_processing_thread_stack,                        
                    K_THREAD_STACK_SIZEOF(accel_data_processing_thread_stack), 
                    accel_data_processing_thread_func,                         
                    NULL, NULL, NULL,                                          
                    K_PRIO_PREEMPT(0),                                         
                    0,                                                         
                    K_MSEC(1000));                                             
    k_thread_name_set(&accel_data_processing_thread_data, "Accel Data Processing Thread");

    return ret;
}

void accel_data_processing_thread_func(void *p1, void *p2, void *p3)
{

    peak_accel_data win_pkt[WIN_N] = {0};
    uint64_t win_t_ms[WIN_N] = {0};
    uint8_t filled = 0; 
    uint64_t last_peak_ms = 0;
    
    uint32_t w = 0;     

    static uint32_t global_index = 0;

    prev_peak_info_t prev_peak = {0};
    printk("==========================================\n");
    printk("[ACC_DATA_P] data processing thread start\n");

    while (1) {
        
        accel_msgq_packet acc_p;
        k_msgq_get(&accel_msgq, &acc_p, K_FOREVER); 
        
        sdcard_accel_data sd;
        convert_acc_data(&acc_p, &sd);
#if RECORD_DETECTED_PEAK_TIME && FFH_INFERENCE == 0
        k_msgq_put(&accel_sd_msgq, &sd, K_FOREVER); 
#endif
        
        peak_accel_data mag = {0};
        calculate_mag_acc_data(&sd, &mag);

        mag.ts_ms = acc_p.acc_t_ms;
        mag.sample_index = global_index;
        global_index++;

        win_pkt[w] = mag;

        w = (w + 1) % WIN_N;
        if ((filled == 0) && (w == 0))
            filled = 1;
        if (filled == 0)
            continue;

        peak_accel_data detected_peak = {0};

        if (detect_peak(win_pkt, w, &last_peak_ms, &detected_peak))
        {
#if RECORD_DETECTED_PEAK_TIME > 0
            detected_peak_t detected_peak_time;
            
            detected_peak_time.ts_ms = k_uptime_get();
            detected_peak_time.ts_ms = detected_peak_time.ts_ms - detected_peak.ts_ms;
            detected_peak_time.sample_index = global_index;
            k_msgq_put(&detected_time_msgq, &detected_peak_time, K_NO_WAIT);
#endif
            int32_t detected_mag_ms2_q16 = mag2q32_to_magq16(detected_peak.mag2_ms2_q32);
            int32_t detected_amp_ms2_q16 = detected_peak.peak_amp_ms2_q16;

            if (ffh_check_cond1(detected_mag_ms2_q16, detected_amp_ms2_q16))
            {
                uint32_t pre_peak_gap = 0;
                uint8_t pre_peak_found = ffh_check_cond3_with_prev_peak(
                    &prev_peak,
                    detected_peak.sample_index,
                    detected_mag_ms2_q16,
                    detected_amp_ms2_q16,
                    &pre_peak_gap);

                register_pending_candidate(
                    detected_peak.sample_index,
                    detected_peak.ts_ms,
                    detected_mag_ms2_q16,
                    detected_amp_ms2_q16,
                    pre_peak_found,
                    pre_peak_gap);
#if Function_Check_Print > 0
                printk("[FFH] candidate registered | idx=%u ts=%llu mag=%.2f amp=%.2f pre=%d gap=%u\n",
                       detected_peak.sample_index,
                       detected_peak.ts_ms,
                       (double)detected_mag_ms2_q16 / 65536.0,
                       (double)detected_amp_ms2_q16 / 65536.0,
                       pre_peak_found,
                       pre_peak_gap);
#endif
            } 
            
            prev_peak.valid = 1;
            prev_peak.sample_index = detected_peak.sample_index;
            prev_peak.ts_ms = detected_peak.ts_ms;
            prev_peak.mag_ms2_q16 = detected_mag_ms2_q16;
            prev_peak.amp_ms2_q16 = detected_amp_ms2_q16;
        } 

        {
            int32_t current_mag_ms2_q16 = mag2q32_to_magq16(mag.mag2_ms2_q32);
            update_pending_candidates_with_sample(
                mag.sample_index,
                current_mag_ms2_q16);
        }
    } 
} 

static inline bool ffh_check_cond1(
    int32_t mag_ms2_q16,
    int32_t amp_ms2_q16)
{
    return (mag_ms2_q16 >= FFH_MAG_THRESH_Q16 &&
            amp_ms2_q16 >= FFH_AMP_THRESH_Q16);
}

static void update_pending_post_window(void)
{
    for (int i = 0; i < MAX_PENDING_FFH; i++)
    {
        if (!ffh_pending[i].used)
            continue;

        ffh_pending[i].collected_samples++;

        if (ffh_pending[i].collected_samples >= 50)
        {
            
            k_msgq_put(&ffh_msgq, &ffh_pending[i], K_NO_WAIT);

            ffh_pending[i].used = 0;
        }
    }
}

static bool ffh_check_cond3_with_prev_peak(
    const prev_peak_info_t *prev_peak,
    uint32_t current_index,
    int32_t current_mag_ms2_q16,
    int32_t current_amp_ms2_q16,
    uint32_t *out_gap)
{
    if (!prev_peak->valid)
        return false;

    if (current_index <= prev_peak->sample_index)
        return false;

    uint32_t gap = current_index - prev_peak->sample_index;

    if (gap > 40)
        return false;

    if (prev_peak->mag_ms2_q16 < current_mag_ms2_q16 &&
        prev_peak->amp_ms2_q16 < current_amp_ms2_q16)
    {
        *out_gap = gap;
        return true;
    }

    return false;
}

static void register_pending_candidate(
    uint32_t peak_index,
    uint64_t peak_ts_ms,
    int32_t peak_mag_ms2_q16,
    int32_t peak_amp_ms2_q16,
    uint8_t pre_peak_found,
    uint32_t pre_peak_gap)
{
    for (int i = 0; i < MAX_PENDING_FFH; i++)
    {
        if (!ffh_pending[i].used)
        {
            ffh_pending[i].used = 1;

            ffh_pending[i].peak_index = peak_index;
            ffh_pending[i].peak_ts_ms = peak_ts_ms;
            ffh_pending[i].peak_mag_ms2_q16 = peak_mag_ms2_q16;
            ffh_pending[i].peak_amp_ms2_q16 = peak_amp_ms2_q16;

            ffh_pending[i].pre_peak_found = pre_peak_found;
            ffh_pending[i].pre_peak_gap = pre_peak_gap;

            ffh_pending[i].collected_samples = 0;

            for (int s = 0; s < 5; s++)
            {
                ffh_pending[i].seg_sum_ms2_q16[s] = 0;
                ffh_pending[i].seg_count[s] = 0;
            }
            return;
        }
    }

    printk("[FFH] pending buffer full\n");
}
static void update_pending_candidates_with_sample(
    uint32_t current_sample_index,
    int32_t current_mag_ms2_q16)
{
    for (int i = 0; i < MAX_PENDING_FFH; i++)
    {
        if (!ffh_pending[i].used)
            continue;

        if (current_sample_index <= ffh_pending[i].peak_index)
            continue;

        if (ffh_pending[i].collected_samples >= 50)
            continue;

        uint8_t seg = ffh_pending[i].collected_samples / 10;

        if (seg < 5)
        {
            ffh_pending[i].seg_sum_ms2_q16[seg] += current_mag_ms2_q16;
            ffh_pending[i].seg_count[seg]++;
        }

        ffh_pending[i].collected_samples++;

        if (ffh_pending[i].collected_samples == 50)
        {
            ffh_candidate_msg_t msg = {0};

            msg.peak_index = ffh_pending[i].peak_index;
            msg.peak_ts_ms = ffh_pending[i].peak_ts_ms;
            msg.peak_mag_ms2_q16 = ffh_pending[i].peak_mag_ms2_q16;
            msg.peak_amp_ms2_q16 = ffh_pending[i].peak_amp_ms2_q16;

            msg.pre_peak_found = ffh_pending[i].pre_peak_found;
            msg.pre_peak_gap = ffh_pending[i].pre_peak_gap;

            msg.stable_count = 0;

            for (int s = 0; s < 5; s++)
            {
                if (ffh_pending[i].seg_count[s] > 0)
                {
                    int32_t mean_ms2_q16 =
                        (int32_t)(ffh_pending[i].seg_sum_ms2_q16[s] /
                                  ffh_pending[i].seg_count[s]);

                    if (mean_ms2_q16 >= STABLE_LOW_Q16 &&
                        mean_ms2_q16 <= STABLE_HIGH_Q16)
                    {
                        msg.stable_count++;
                    }
                }
            }

            if (k_msgq_put(&ffh_candidate_msgq, &msg, K_NO_WAIT) != 0)
            {
                printk("[FFH] ffh_candidate_msgq full\n");
            }

            ffh_pending[i].used = 0;
        }
    }
}

bool detect_peak(
        const peak_accel_data *win_pkt,
        uint32_t w,
        uint64_t *last_peak_ms,
        peak_accel_data *detected_peak
    )
{
    
    uint32_t center = (w + WIN_N - 1 - WIN_R) % WIN_N;
    
    if(win_pkt[center].mag2_ms2_q32 < PEAK_MAG2_THRESH_MS2_Q32)
    {
        return false;
    }
    
    uint32_t l[WIN_L], r[WIN_R];
    for (int i = 0; i < WIN_L; i++)
        l[i] = (center + WIN_N - (i + 1)) % WIN_N;

    for (int i = 0; i < WIN_R; i++)
        r[i] = (center + (i + 1)) % WIN_N;
    
    int64_t mc = win_pkt[center].mag2_ms2_q32;
    if (mc < win_pkt[l[0]].mag2_ms2_q32 ||
        mc < win_pkt[l[1]].mag2_ms2_q32 ||
        mc < win_pkt[r[0]].mag2_ms2_q32 ||
        mc < win_pkt[r[1]].mag2_ms2_q32)
        return false;
    
    uint64_t t_c = win_pkt[center].ts_ms;
    if (*last_peak_ms && (t_c - *last_peak_ms) < MIN_PEAK_INTERVAL_MS)
        return false;
    
    uint64_t sumL = 0, sumR = 0;

    for (int i = 0; i < WIN_L; i++)
        sumL += win_pkt[l[i]].mag2_ms2_q32;

    for (int i = 0; i < WIN_R; i++)
        sumR += win_pkt[r[i]].mag2_ms2_q32;

    uint64_t avgL = (sumL + WIN_L / 2) / WIN_L;
    uint64_t avgR = (sumR + WIN_R / 2) / WIN_R;

    if (avgL < AVG_MAG2_THRESH_MS2_Q32 ||
        avgR < AVG_MAG2_THRESH_MS2_Q32)
        return false;
    
    uint64_t L_min = win_pkt[l[0]].mag2_ms2_q32;
    for (int i = 1; i < WIN_L; i++)
        if (win_pkt[l[i]].mag2_ms2_q32 < L_min)
            L_min = win_pkt[l[i]].mag2_ms2_q32;

    uint64_t R_min = win_pkt[r[0]].mag2_ms2_q32;
    for (int i = 1; i < WIN_R; i++)
        if (win_pkt[r[i]].mag2_ms2_q32 < R_min)
            R_min = win_pkt[r[i]].mag2_ms2_q32;

    uint64_t b = (L_min > R_min) ? L_min : R_min;

    int32_t peak_mag_q16 = mag2q32_to_magq16(mc);
    int32_t base_mag_q16 = mag2q32_to_magq16(b);

    int32_t amp_ms2_q16 = peak_mag_q16 - base_mag_q16;
    if (amp_ms2_q16 < 0)
        amp_ms2_q16 = 0;
    
    if (amp_ms2_q16 < PEAK_AVG_MAG_THRESH_MS2_Q16)
        return false;
    
    *detected_peak = win_pkt[center];

    detected_peak->is_peak = 1;
    detected_peak->peak_amp_ms2_q16 = amp_ms2_q16;
    detected_peak->peak_interval_ms = (*last_peak_ms == 0) ? 0 : (t_c - *last_peak_ms);

    *last_peak_ms = t_c;

    return true;
}

void convert_acc_data(const accel_msgq_packet *acc_p, sdcard_accel_data *sd_acc_p)
{
    sanitize_sensor_value(&acc_p->acc[0]);
    sanitize_sensor_value(&acc_p->acc[1]);
    sanitize_sensor_value(&acc_p->acc[2]);

    double acc_x = acc_p->acc[0].val1 + acc_p->acc[0].val2 / 1e6 - adxl362_offset_x;
    double acc_y = acc_p->acc[1].val1 + acc_p->acc[1].val2 / 1e6 - adxl362_offset_y;
    double acc_z = acc_p->acc[2].val1 + acc_p->acc[2].val2 / 1e6 - adxl362_offset_z;

    sd_acc_p->acc[0].val1 = (int)acc_x;
    sd_acc_p->acc[0].val2 = (int)((acc_x - sd_acc_p->acc[0].val1) * 1e6);
    sd_acc_p->acc[1].val1 = (int)acc_y;
    sd_acc_p->acc[1].val2 = (int)((acc_y - sd_acc_p->acc[1].val1) * 1e6);
    sd_acc_p->acc[2].val1 = (int)acc_z;
    sd_acc_p->acc[2].val2 = (int)((acc_z - sd_acc_p->acc[2].val1) * 1e6);

    uint64_t time = acc_p->acc_t_ms;
    sd_acc_p->millis = time % 1000; time /= 1000;
    sd_acc_p->second = time % 60;   time /= 60;
    sd_acc_p->minute = time % 60;   time /= 60;
    sd_acc_p->hour = time % 24;     time /= 24;
    sd_acc_p->day = time % 30;
    sd_acc_p->month = time / 30;
}

void calculate_mag_acc_data(const sdcard_accel_data *sd_acc_p, peak_accel_data *peak_acc_p)
{
    
    int32_t xq = sensor_val_q16(&sd_acc_p->acc[0]);
    int32_t yq = sensor_val_q16(&sd_acc_p->acc[1]);
    int32_t zq = sensor_val_q16(&sd_acc_p->acc[2]);
    
    peak_acc_p->mag2_ms2_q32 = q16_square(xq) + q16_square(yq) + q16_square(zq); 

    peak_acc_p->is_peak = 0;
    peak_acc_p->peak_amp_ms2_q16 = 0;
    peak_acc_p->peak_interval_ms = 0;
}

    void sanitize_sensor_value(struct sensor_value *v)
{
    if (v->val2 < 0) {
        v->val1 -= 1;
        v->val2 += 1000000;
    }
}

static inline int32_t sensor_val_q16(const struct sensor_value *v)
{
    int64_t x = ((int64_t)v->val1 << 16) + (((int64_t)v->val2 << 16) / 1000000);
    return (int32_t)x;
}

static inline int64_t q16_square(int32_t q16)
{
    return (int64_t)q16 * (int64_t)q16; 
}

static inline uint32_t isqrt64(uint64_t x)
{
    uint64_t op = x, res = 0, one = (uint64_t)1 << 62;
    while (one > op )
        one >>= 2;
    while(one)
    {
        if(op >= res + one) {
            op -= res + one;
            res = (res >> 1) + one;
        }
        else{
            res >>= 1;
        }
        one >>= 2;
    }
    return (uint32_t)res; 
}

static inline uint64_t mag_q16_from_pkt(const sdcard_accel_data *p)
{
    int32_t xq = sensor_val_q16(&p->acc[0]);
    int32_t yq = sensor_val_q16(&p->acc[1]);
    int32_t zq = sensor_val_q16(&p->acc[2]);
    uint64_t mag2_q32 = (uint64_t)q16_square(xq) + q16_square(yq) + q16_square(zq);
    return mag2_q32;
}
static inline uint32_t mag2q32_to_magq16(uint64_t mag2_ms2_q32)
{
    return (uint32_t)isqrt64(mag2_ms2_q32); 
}
