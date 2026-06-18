                                                                                                  
 
 
 
                                                                                                  
file_name = ''                      
                                       
                                      
                                       
PLOT_CFG = {
                         
    "width": 3700,
    "height": 1400,

                    
    "margin": {
        "l": 80,
        "r": 120,                   
        "t": 90,
        "b": 60
    },

            
    "legend": {
        "orientation": "h",
        "y": 1.08
    }
}

import re
import plotly.io as pio
pio.renderers.default = "vscode"


def validate_sensor_file(file_path, expected_fields, time_format="%m-%d %H:%M:%S.%f"):



    issues = []
    line_num = 0

    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        for raw_line in f:
            line_num += 1
            line = raw_line.rstrip("\n")

                                                           
                            
                                                           
            if "\x00" in line:
                issues.append((line_num, "NULL 바이트 포함", repr(line)))

                                     
                line = line.replace("\x00", "")

                   
            if line.strip() == "":
                issues.append((line_num, "빈 줄", line))
                continue

                                                           
                         
                                                           
            parts = [p.strip() for p in line.split(",")]
            if len(parts) != expected_fields:
                issues.append((line_num, f"필드 수 오류 (현재 {len(parts)}, 기대 {expected_fields})", line))
                continue

                                                           
                               
                            
                                                           
            time_str = parts[1]

                                                
            if not re.match(r"\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3}", time_str):
                issues.append((line_num, "시간 형식 비정상", time_str))
                continue

                               
            try:
                _ = datetime.strptime(time_str, time_format)
            except Exception:
                issues.append((line_num, "datetime 파싱 실패", time_str))
                continue

                                                   
           
                                                   

    if len(issues) == 0:
       
    else:
        

        for i, (ln, err, content) in enumerate(issues[:20], start=1):
            print(f" {i}) Line {ln} → {err}: {content}")

        if len(issues) > 20:
            print(f"... (총 {len(issues)}건 중 앞 20개만 표시)")

    return issues
                                         
import os
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
from datetime import timedelta
from math import sqrt
import matplotlib.dates as mdates
                                 
     
                                 
DEBUG_MODE = False

if DEBUG_MODE :
        

                        
file_path_acc = '../../(DataSet)/ACC/'
file_path_env = '../../(DataSet)/ENV/'
           
file_name_base = file_name
               
file_type_acc = '_ACC'
file_type_env = '_ENV'
file_sort = '_date_set'
file_ext = '.txt'
                            
acc_full_path = os.path.join(file_path_acc+file_name_base+file_type_acc+file_sort+file_ext)
env_full_path = os.path.join(file_path_env+file_name_base+file_type_env+file_sort+file_ext)

print("ACC full path:", acc_full_path)
print("ENV full path:", env_full_path)
                                                                     
             
                                                                     

def check_file_exists(path, label):
    if not os.path.exists(path):
        return False
    else:
        return True

acc_exists = check_file_exists(acc_full_path, "ACC")
env_exists = check_file_exists(env_full_path, "ENV")

                                 
      
                                 
gravity_acc = 9.80665
Q16_Trans_Num = 65536.0
WIN_L = 5
WIN_R = 5
PEAK_CHECK_LEFT = 2
PEAK_CHECK_RIGHT = 2
AVG_MAG_THRESH_G = 1.10         
AVG_MAG_THRESH_MS = AVG_MAG_THRESH_G * gravity_acc           
AVG_MAG_THRESH_Q16 = int(AVG_MAG_THRESH_MS * Q16_Trans_Num)
AVG_MAG_THRESH_Q32 = AVG_MAG_THRESH_Q16 * AVG_MAG_THRESH_Q16
             
WINDOW_SEC = 10          
FIGSIZE = (30, 16)
PROM_THRESH_G = 0.20                       
PROM_THRESH_MS = PROM_THRESH_G * gravity_acc
PROM_THRESH_Q16 = int(PROM_THRESH_MS * Q16_Trans_Num)
Y_AXIS_LIMIT_G = 10
                                 
           
                                 
def sensor_val_to_q16(val1, val2):
    return (val1 << 16) + (val2 * 65536) // 1_000_000

def q16_square(xq16):
    return xq16 * xq16

def compute_mag2_ms_q32(ax_ms_q16, ay_ms_q16, az_ms_q16):
    return q16_square(ax_ms_q16) + q16_square(ay_ms_q16) + q16_square(az_ms_q16)

def q32_to_q16(q32_val):
    return q32_val >> 16

def ms_q32_to_ms_q16(ms_q32):
    return 

def ms2_q32_to_g(ms2_q32):
    return (sqrt(ms2_q32)/Q16_Trans_Num)/gravity_acc

def ms_q16_to_g(ms_q16):
    return (ms_q16/Q16_Trans_Num)/gravity_acc
                                                                     
                                                 
                                                                     

def load_env_file(full_file_path):
    sequence_list = []
    time_list = []
    flag_env = []
    temperature = []
    humidity = []
    pressure = []
    gas = []
    iaq = []
    eco2 = []
    bvoc = []
    per = []

    with open(full_file_path, 'r', encoding='utf-8') as file:
        for line in file:
            parts = line.strip().split(',')

                    
            sequence_list.append(int(parts[0].strip()))

                             
                                       
            time_str = parts[1].strip()
            dt = datetime.strptime(f"2025-{time_str}", "%Y-%m-%d %H:%M:%S.%f")
            time_list.append(dt)

            flag_env.append(int(parts[2]))
            temperature.append(int(parts[3]) / 1000)
            humidity.append(int(parts[4]) / 1000)
            pressure.append(int(parts[5]) / 100)
            gas.append(int(parts[6]) / 1000)
            iaq.append(int(parts[7]) / 1000)
            eco2.append(int(parts[8]) / 1000)
            bvoc.append(int(parts[9]) / 100000)
            per.append(int(parts[10]) / 10000)

    df = pd.DataFrame({
        "Sequence": sequence_list,
        "Time": time_list,                     
        "Flag": flag_env,
        "Temperature (°C)": temperature,
        "Humidity (%)": humidity,
        "Pressure (hPa)": pressure,
        "Gas Resistance (KΩ)": gas,
        "IAQ Index": iaq,
        "eCO2 (ppm)": eco2,
        "BVOC (ppm)": bvoc,
        "Percentage (%)": per
    })

    return df

                                                                     
                              
                                                                     
def load_acc_file(full_file_path):
    seq_list = []
    time_list = []
    ax_v1 = []
    ax_v2 = []
    ay_v1 = []
    ay_v2 = []
    az_v1 = []
    az_v2 = []

    with open(full_file_path, "r", encoding="utf-8") as f:
        for line in f:
            parts = line.strip().split(',')
            
                          
            if len(parts) < 8:
                print("⚠ 잘못된 라인:", parts)
                continue

            seq_list.append(int(parts[0]))

                     
            time_str = parts[1].strip()                        
            dt = datetime.strptime(f"2025-{time_str}", "%Y-%m-%d %H:%M:%S.%f")
            time_list.append(dt)

            ax_v1.append(int(parts[2]))
            ax_v2.append(int(parts[3]))
            ay_v1.append(int(parts[4]))
            ay_v2.append(int(parts[5]))
            az_v1.append(int(parts[6]))
            az_v2.append(int(parts[7]))

    df = pd.DataFrame({
        "Sequence": seq_list,
        "Time": time_list,
        "ax_val1": ax_v1, "ax_val2": ax_v2,
        "ay_val1": ay_v1, "ay_val2": ay_v2,
        "az_val1": az_v1, "az_val2": az_v2
    })

            
    df["ax_ms_q16"] = [sensor_val_to_q16(v1, v2) for v1, v2 in zip(df["ax_val1"], df["ax_val2"])]
    df["ay_ms_q16"] = [sensor_val_to_q16(v1, v2) for v1, v2 in zip(df["ay_val1"], df["ay_val2"])]
    df["az_ms_q16"] = [sensor_val_to_q16(v1, v2) for v1, v2 in zip(df["az_val1"], df["az_val2"])]

               
    df["mag2_ms_q32"] = [
        compute_mag2_ms_q32(x, y, z)
        for x, y, z in zip(df["ax_ms_q16"], df["ay_ms_q16"], df["az_ms_q16"])
    ]
    df["mag_ms"] = [sqrt(m2) / Q16_Trans_Num for m2 in df["mag2_ms_q32"]]
    df["mag_g"] = df["mag_ms"] / gravity_acc

    return df

                                                                     
             
                                                                     
import plotly.graph_objects as go

def plot_acc_env_overlap_plotly(
    acc_df, env_df,
    y_limits=None,
    title=None,
    fig_width=1400,
    fig_height=700,
    peaks_df=None,
    fall_stage_peaks=None
):
    fig = go.Figure()

                                     
                    
                                     
    fig.add_trace(go.Scatter(
        x=acc_df["Time"],
        y=acc_df["mag_g"],
        name="ACC |mag| (g)",
        mode="lines",
        line=dict(color="black", width=2),
        customdata=acc_df[["baseline_g", "amp_g", "index"]],
        hovertemplate=(
            "Time: %{x}<br>"
            "Index: %{customdata[2]}<br>"
            "Mag: %{y:.3f} g<br>"
            "Baseline: %{customdata[0]:.3f} g<br>"
            "Amplitude: %{customdata[1]:.3f} g"
            "<extra></extra>"
        )
    ))

    fig.update_yaxes(
        title_text="ACC Magnitude (g)",
        range=y_limits["ACC"] if y_limits and "ACC" in y_limits else None
    )

                                     
                                   
                                     
    if peaks_df is not None and not peaks_df.empty:
        fig.add_trace(go.Scatter(
            x=acc_df.loc[peaks_df["index"], "Time"],
            y=peaks_df["mag_g_peak"],
            mode="markers",
            name="Detected Peaks",
            marker=dict(
                color="orange",
                size=8,
                symbol="circle"
            ),
            customdata=peaks_df[["prom_g", "base_g"]],
            hovertemplate=(
                "Time: %{x}<br>"
                "Peak mag: %{y:.2f} g<br>"
                "Amplitude: %{customdata[0]:.2f} g<br>"
                "Baseline: %{customdata[1]:.2f} g"
                "<extra></extra>"
            )
        ))

                                                               
                                                
                                                               
    if fall_stage_peaks:

                                                      
                                       
        if y_limits and "ACC" in y_limits:
            y_top = y_limits["ACC"][1]
        else:
            y_top = acc_df["mag_g"].max()

        STAGE_ORDER = ["final_fall", "cond5", "cond4", "cond3", "cond2"]
        STAGE_Y_OFFSET = 0.4

        stage_y_map = {
            stage: y_top - i * STAGE_Y_OFFSET
            for i, stage in enumerate(STAGE_ORDER)
        }

                
        PASS_STYLE = {
            "cond2": dict(color="purple", symbol="diamond"),
            "cond3": dict(color="blue",   symbol="square"),
            "cond4": dict(color="green",  symbol="triangle-right"),
            "cond5": dict(color="orange", symbol="diamond-open"),
            "final_fall": dict(color="black", symbol="triangle-down"),
        }
        FAIL_STYLE = dict(symbol="x", size=12, color="gray")

                                         
                                                
                                         
        df2 = fall_stage_peaks.get("cond2_window")
        if df2 is not None and not df2.empty:
            fig.add_trace(go.Scatter(
                x=acc_df.loc[df2["index"], "Time"],
                y=[stage_y_map["cond2"]] * len(df2),
                mode="markers",
                name="cond2 PASS",
                marker=dict(
                    size=10,
                    **PASS_STYLE["cond2"]
                ),
                hovertemplate=(
                    "Time: %{x}<br>"
                    "Stage: cond2 (window ok)<extra></extra>"
                )
            ))

                                         
                                
                                         
        df3_all = fall_stage_peaks.get("cond3_pre")
        cond3_pass = None
        cond3_fail = None
        if df3_all is not None and not df3_all.empty:
            cond3_pass = df3_all[df3_all["cond3_pass"]]
            cond3_fail = df3_all[~df3_all["cond3_pass"]]

                  
            if not cond3_pass.empty:
                fig.add_trace(go.Scatter(
                    x=acc_df.loc[cond3_pass["index"], "Time"],
                    y=[stage_y_map["cond3"]] * len(cond3_pass),
                    mode="markers",
                    name="cond3 PASS",
                    marker=dict(
                        size=10,
                        **PASS_STYLE["cond3"]
                    ),
                    hovertemplate=(
                        "Time: %{x}<br>"
                        "cond3: PASS<extra></extra>"
                    )
                ))

                      
            if not cond3_fail.empty:
                fig.add_trace(go.Scatter(
                    x=acc_df.loc[cond3_fail["index"], "Time"],
                    y=[stage_y_map["cond3"]] * len(cond3_fail),
                    mode="markers",
                    name="cond3 FAIL",
                    marker=FAIL_STYLE,
                    customdata=cond3_fail[["cond3_reason"]],
                    hovertemplate=(
                        "Time: %{x}<br>"
                        "cond3: FAIL<br>"
                        "Reason: %{customdata[0]}<extra></extra>"
                    )
                ))

                                         
                                
                                         
        df4_all = fall_stage_peaks.get("cond4_post")
        cond4_pass = None
        cond4_fail = None
        if df4_all is not None and not df4_all.empty:
            cond4_pass = df4_all[df4_all["cond4"]]
            cond4_fail = df4_all[~df4_all["cond4"]]

            if not cond4_pass.empty:
                fig.add_trace(go.Scatter(
                    x=acc_df.loc[cond4_pass["index"], "Time"],
                    y=[stage_y_map["cond4"]] * len(cond4_pass),
                    mode="markers",
                    name="cond4 PASS",
                    marker=dict(
                        size=10,
                        **PASS_STYLE["cond4"]
                    ),
                    hovertemplate=(
                        "Time: %{x}<br>"
                        "cond4: PASS<extra></extra>"
                    )
                ))

            if not cond4_fail.empty:
                fig.add_trace(go.Scatter(
                    x=acc_df.loc[cond4_fail["index"], "Time"],
                    y=[stage_y_map["cond4"]] * len(cond4_fail),
                    mode="markers",
                    name="cond4 FAIL",
                    marker=FAIL_STYLE,
                    customdata=cond4_fail[["cond4_reason", "max_consecutive_stable"]],
                    hovertemplate=(
                        "Time: %{x}<br>"
                        "cond4: FAIL<br>"
                        "max_consecutive: %{customdata[1]}<br>"
                        "Reason: %{customdata[0]}<extra></extra>"
                    )
                ))

                                         
                                     
                                           
                                         
        df5_all = fall_stage_peaks.get("cond5_all")
        cond5_fail = None
        if df5_all is not None and not df5_all.empty:
            cond5_fail = df5_all[~df5_all["cond5"]]

            if not cond5_fail.empty:
                fig.add_trace(go.Scatter(
                    x=acc_df.loc[cond5_fail["index"], "Time"],
                    y=[stage_y_map["cond5"]] * len(cond5_fail),
                    mode="markers",
                    name="cond5 FAIL (pressure)",
                    marker=FAIL_STYLE,
                    customdata=cond5_fail[[
                        "pressure_dp_hpa",
                        "height_drop_m",
                        "pressure_dir"
                    ]],
                    hovertemplate=(
                        "Time: %{x}<br>"
                        "cond5: FAIL<br>"
                        "ΔP sum: %{customdata[0]:+.3f} hPa<br>"
                        "Δh: %{customdata[1]:.2f} m<br>"
                        "Dir: %{customdata[2]}<extra></extra>"
                    )
                ))

                                         
                                        
                                         
        df_final = fall_stage_peaks.get("final_fall")
        if df_final is not None and not df_final.empty:
            fig.add_trace(go.Scatter(
                x=acc_df.loc[df_final["index"], "Time"],
                y=[stage_y_map["final_fall"]] * len(df_final),
                mode="markers",
                name="FINAL Fall-from-height",
                marker=dict(
                    symbol=PASS_STYLE["final_fall"]["symbol"],
                    size=16,
                    color=PASS_STYLE["final_fall"]["color"],
                    line=dict(width=1, color="white")
                ),
                customdata=df_final[["mag_g_peak", "prom_g", "height_drop_m"]],
                hovertemplate=(
                    "Time: %{x}<br>"
                    "FINAL Fall<br>"
                    "Peak mag: %{customdata[0]:.2f} g<br>"
                    "Amplitude: %{customdata[1]:.2f} g<br>"
                    "Est. height drop: %{customdata[2]:.2f} m"
                    "<extra></extra>"
                )
            ))

                                                               
                                                  
                                                               
    if fall_stage_peaks and "cond2_window" in fall_stage_peaks:
        cond2_df = fall_stage_peaks["cond2_window"]
        Y_EPS = 0.05

        for _, r in cond2_df.iterrows():
            i = int(r["index"])
            peak_y = r["mag_g_peak"]

            x0 = _idx_to_time(acc_df, max(0, i - 40))
            x1 = _idx_to_time(acc_df, min(len(acc_df) - 1, i + 40))

            fig.add_shape(
                type="rect",
                x0=x0, x1=x1,
                y0=peak_y - Y_EPS,
                y1=peak_y + Y_EPS,
                fillcolor="rgba(0, 0, 255, 0.25)",
                line_width=0,
                layer="above"
            )

                                                               
                                                 
                                      
                                       
                                                               
    if fall_stage_peaks and "cond3_pre" in fall_stage_peaks:
        cond3_df = fall_stage_peaks["cond3_pre"]

        COLORS = [
            "rgba(0, 200, 0, 0.15)",
            "rgba(0, 160, 0, 0.15)",
            "rgba(0, 120, 0, 0.15)",
            "rgba(0, 80, 0, 0.15)",
            "rgba(0, 40, 0, 0.15)",
        ]
        Y_EPS = 0.06

            
        for _, r in cond3_df.iterrows():
            i = int(r["index"])
            peak_y = r["mag_g_peak"]

            for k in range(5):
                s = i + 1 + k * 10
                e = i + 1 + (k + 1) * 10

                if e >= len(acc_df):
                    continue

                x0 = _idx_to_time(acc_df, s)
                x1 = _idx_to_time(acc_df, e)

                fig.add_shape(
                    type="rect",
                    x0=x0, x1=x1,
                    y0=peak_y - Y_EPS,
                    y1=peak_y + Y_EPS,
                    fillcolor=COLORS[k],
                    line_width=0,
                    layer="above"
                )

                          
        for _, r in cond3_df.iterrows():
            i = int(r["index"])
            peak_y = r["mag_g_peak"]

            for k in range(5):
                s = i + 1 + k * 10
                e = i + 1 + (k + 1) * 10

                if e >= len(acc_df):
                    continue

                seg = acc_df.iloc[s:e]
                mean_g = seg["mag_g"].mean()
                x_mid = _idx_to_time(acc_df, (s + e) // 2)

                fig.add_annotation(
                    x=x_mid,
                    y=peak_y + Y_EPS + 0.01,            
                    text=f"{mean_g:.2f}g",
                    showarrow=False,
                    font=dict(size=10, color="green"),
                    align="center"
                )

                                     
                         
                                     
    env_sensors = [
        ("Temperature (°C)", "red"),
        ("Humidity (%)", "blue"),
        ("Pressure (hPa)", "green"),
        ("Gas Resistance (KΩ)", "purple"),
        ("IAQ Index", "orange"),
        ("eCO2 (ppm)", "brown"),
        ("BVOC (ppm)", "pink"),
    ]

    axis_count = 1
    for col_name, color in env_sensors:
        if col_name not in env_df:
            continue

        axis_count += 1
        layout_axis = f"yaxis{axis_count}"
        trace_axis  = f"y{axis_count}"

        fig.add_trace(go.Scatter(
            x=env_df["Time"],
            y=env_df[col_name],
            name=col_name,
            mode="lines+markers",
            yaxis=trace_axis,
            line=dict(color=color),
        ))

        axis_cfg = dict(
            title=dict(text=col_name, font=dict(color=color)),
            tickfont=dict(color=color),
            overlaying="y",
            side="right",
            anchor="x",
            position=min(1.0, 1.0 - 0.02 * (axis_count - 2))
        )

        if y_limits and col_name in y_limits:
            axis_cfg["range"] = y_limits[col_name]

        fig.update_layout({layout_axis: axis_cfg})

                                     
                                
                                     
    fig.update_layout(
        title=title,
        hovermode="x unified",
        dragmode="zoom",
        width=PLOT_CFG["width"],
        height=PLOT_CFG["height"],
        margin=PLOT_CFG["margin"],
        legend=PLOT_CFG["legend"],
        xaxis=dict(title=dict(text="Time"))
    )

    x_start = min(acc_df["Time"].min(), env_df["Time"].min())
    x_end   = max(acc_df["Time"].max(), env_df["Time"].max())
    fig.update_xaxes(range=[x_start, x_end], automargin=False)

    fig.show()

from datetime import timedelta

                                                                                                              
plot_segment_10sec = 10
plot_segment_30sec = 30
plot_segment_5minute = 60*5
plot_segment_10minute = 60*10
plot_segment_30minute = 60*30
plot_width = 35
plot_height = 15

y_limits_base = {
    "ACC": (0, 8.0),
    "Temperature (°C)": (0, 40),
    "Humidity (%)": (30, 80),
    "Pressure (hPa)": (1000, 1010),
    "Gas Resistance (KΩ)": (0, 20000),
    "IAQ Index": (0, 500),
    "eCO2 (ppm)": (300, 6000),
    "BVOC (ppm)": (0, 3)
}
env_auto_margin = {
    "Temperature (°C)": 3.0,
    "Humidity (%)": 10.0,
    "Pressure (hPa)": 1.0,
}
env_auto_margin_short = {
    "Temperature (°C)": 1.0,
    "Humidity (%)": 5.0,
    "Pressure (hPa)": 0.2,
}
env_auto_sensors = [
    "Temperature (°C)",
    "Humidity (%)",
    "Pressure (hPa)",
    "Gas Resistance (KΩ)",
    "IAQ Index",
    "eCO2 (ppm)",
    "BVOC (ppm)"
]
                                                                                                              
                                                                     
  
                                                                     
def build_segment_y_limits(env_seg, y_limits_base, env_auto_margin):
    """
    segment 단위 env_seg에서
    자동 적용 센서는 mean±margin으로 계산
    자동 적용되지 않는 센서는 y_limits_base 그대로 사용
    """
    y_limits_final = y_limits_base.copy()

    for col_name, margin in env_auto_margin.items():
        if col_name in env_seg and len(env_seg[col_name]) > 0:
            mean_val = env_seg[col_name].mean()
            y_limits_final[col_name] = (mean_val - margin, mean_val + margin)

    return y_limits_final
                                                                     
  
                                                                     
def build_segment_y_limits_minmax(env_seg, y_limits_base, env_auto_sensors):
    """
    segment 내부에서:
      - 자동 센서는 최소~최대 범위
      - 나머지 센서는 base 값 유지
    """
    y_limits_final = y_limits_base.copy()

    for col_name in env_auto_sensors:
        if col_name in env_seg and len(env_seg[col_name]) > 0:
            ymin = env_seg[col_name].min()
            ymax = env_seg[col_name].max()
            y_limits_final[col_name] = (ymin, ymax)

    return y_limits_final
                                                                     
  
                                                                     
def choose_segment_y_limits(env_seg, y_limits_base,
                            env_auto_margin,
                            env_auto_sensors,
                            segment_sec,
                            env_auto_margin_short=None):
    if segment_sec >= 600:
        return build_segment_y_limits_minmax(
            env_seg, y_limits_base, env_auto_sensors
        )

    if segment_sec < 120 and env_auto_margin_short is not None:
        return build_segment_y_limits(
            env_seg, y_limits_base, env_auto_margin_short
        )

    return build_segment_y_limits(
        env_seg, y_limits_base, env_auto_margin
    )

                                                                     
  
                                                                     
def plot_acc_env_overlap_segmented_plotly(
    acc_df, env_df,
    segment_sec=10,
    fig_width=1400,
    fig_height=700
):
    dataset_start_time = min(acc_df["Time"].min(), env_df["Time"].min())
    dataset_end_time   = max(acc_df["Time"].max(), env_df["Time"].max())

    total_sec = (dataset_end_time - dataset_start_time).total_seconds()
    segment_count = int(total_sec // segment_sec) + 1

    for seg_idx in range(segment_count):
        seg_start = dataset_start_time + timedelta(seconds=seg_idx * segment_sec)
        seg_end   = dataset_start_time + timedelta(seconds=(seg_idx + 1) * segment_sec)

        acc_seg = acc_df[(acc_df["Time"] >= seg_start) & (acc_df["Time"] < seg_end)]
        env_seg = env_df[(env_df["Time"] >= seg_start) & (env_df["Time"] < seg_end)]

        if acc_seg.empty and env_seg.empty:
            continue

        y_limits_seg = choose_segment_y_limits(
            env_seg,
            y_limits_base,
            env_auto_margin,
            env_auto_sensors,
            segment_sec,
            env_auto_margin_short
        )

        title = (
            f"{file_name_base} ACC + ENV — Segment {seg_idx+1}/{segment_count}<br>"
            f"{seg_start.strftime('%H:%M:%S.%f')[:-3]} ~ {seg_end.strftime('%H:%M:%S.%f')[:-3]}"
        )

        plot_acc_env_overlap_plotly(
            acc_seg,
            env_seg,
            y_limits=y_limits_seg,
            title=title,
            fig_width=fig_width,
            fig_height=fig_height
        )

                                                                                                              
              

                                                     
def add_time_columns(acc_df):
    t0 = acc_df["Time"].iloc[0]

    acc_df["elapsed_ms"] = (
        (acc_df["Time"] - t0).dt.total_seconds() * 1000
    ).astype(int)

    acc_df["relative_sec"] = acc_df["elapsed_ms"] / 1000.0

    return acc_df

                                 
                
                                 
                                 
                                             
                                 
LOG_PEAK_SUMMARY     = True              
LOG_PEAK_LOCAL_MAX   = False                     
LOG_PEAK_AMPLITUDE   = False                        
LOG_PEAK_MAG_AVG     = False                        
LOG_PEAK_EACH        = False                      

                                                                     
                                        
                                                                   
                                                    
                                                                     
def compute_local_baseline_and_amplitude(acc_df, win_l=5, win_r=5):
    N = len(acc_df)

    baseline = [None] * N
    amplitude = [None] * N

    mag = acc_df["mag_g"].values

    for i in range(win_l, N - win_r):
        left_min  = mag[i-win_l:i].min()
        right_min = mag[i+1:i+1+win_r].min()

        base = max(left_min, right_min)
        amp  = mag[i] - base

        baseline[i]  = base
        amplitude[i] = amp

    acc_df["baseline_g"] = baseline
    acc_df["amp_g"] = amplitude

    return acc_df

                                                                     
  
                                                                     
def detect_peaks(df):
    total_samples = len(df)

            
    debug_logs = []

                       
    if total_samples < WIN_L + WIN_R + 1:
        return pd.DataFrame(), debug_logs

    if LOG_PEAK_SUMMARY:
        print(f"WIN_L={WIN_L}, WIN_R={WIN_R}")
        print(f"PROM_THRESH_G={PROM_THRESH_G} g")
        print(f"AVG_MAG_THRESH_G={AVG_MAG_THRESH_G} g")

             
    cnt_total = 0
    cnt_local_max = 0
    cnt_amplitude = 0
    cnt_mag_avg = 0
    cnt_final = 0

    peaks = []

    for i in range(WIN_L, total_samples - WIN_R):
        cnt_total += 1

        mc2_q32 = df.iloc[i]["mag2_ms_q32"]

                                                           
                          
                                                           
        l_vals = [df.iloc[i - j]["mag2_ms_q32"] for j in range(1, PEAK_CHECK_LEFT + 1)]
        r_vals = [df.iloc[i + j]["mag2_ms_q32"] for j in range(1, PEAK_CHECK_RIGHT + 1)]

        if not all(mc2_q32 >= v for v in (l_vals + r_vals)):
            continue
        cnt_local_max += 1

        if LOG_PEAK_LOCAL_MAX:
            print(f"[LOCAL_MAX] i={i} t={df.iloc[i]['relative_sec']:.3f}s")

                                                           
                          
                                                           
        left_vals = [df.iloc[i - j]["mag2_ms_q32"] for j in range(1, WIN_L + 1)]
        right_vals = [df.iloc[i + j]["mag2_ms_q32"] for j in range(1, WIN_R + 1)]

        base2_q32 = max(min(left_vals), min(right_vals))
        base_q16 = sqrt(base2_q32)
        mc_q16 = sqrt(mc2_q32)
        prom_q16 = mc_q16 - base_q16

        if prom_q16 < PROM_THRESH_Q16:
            continue
        cnt_amplitude += 1

        base_g = (base_q16 / Q16_Trans_Num) / gravity_acc
        mc_g   = (mc_q16   / Q16_Trans_Num) / gravity_acc
        prom_g = (prom_q16 / Q16_Trans_Num) / gravity_acc

        if LOG_PEAK_AMPLITUDE:
            print(
                f"[AMP] i={i} t={df.iloc[i]['relative_sec']:.3f}s | "
                f"mag={mc_g:.3f}g base={base_g:.3f}g prom={prom_g:.3f}g"
            )

                                                           
                             
                                                           
        avgL_ms_q32 = sum(df.iloc[i - j]["mag2_ms_q32"] for j in range(1, WIN_L + 1)) // WIN_L
        avgR_ms_q32 = sum(df.iloc[i + j]["mag2_ms_q32"] for j in range(1, WIN_R + 1)) // WIN_R

        if avgL_ms_q32 < AVG_MAG_THRESH_Q32 and avgR_ms_q32 < AVG_MAG_THRESH_Q32:
            continue
        cnt_mag_avg += 1

        if LOG_PEAK_MAG_AVG:
            avgL_g = ms2_q32_to_g(avgL_ms_q32)
            avgR_g = ms2_q32_to_g(avgR_ms_q32)
            print(
                f"[AVG] i={i} t={df.iloc[i]['relative_sec']:.3f}s | "
                f"avgL={avgL_g:.3f}g avgR={avgR_g:.3f}g"
            )

                                                           
                 
                                                           
        peak_entry = {
            "index": i,
            "elapsed_ms": df.iloc[i]["elapsed_ms"],
            "relative_sec": df.iloc[i]["relative_sec"],
            "mag_g_peak": mc_g,
            "base_g": base_g,
            "prom_g": prom_g
        }
        peaks.append(peak_entry)
        cnt_final += 1

                      
        debug_logs.append({
            "i": i,
            "time": df.iloc[i]["relative_sec"],
            "mag_g": mc_g,
            "prom_g": prom_g,
            "avgL_q32": avgL_ms_q32,
            "avgR_q32": avgR_ms_q32
        })

        if LOG_PEAK_EACH:
            print(
                f"[PEAK] t={df.iloc[i]['relative_sec']:.3f}s | "
                f"mag={mc_g:.3f}g | amp={prom_g:.3f}g"
            )

                                                       
           
                                                       
    if LOG_PEAK_SUMMARY:


    return pd.DataFrame(peaks), debug_logs
                                                                     
                                 
                                                                     
def debug_peak_at_index(acc_df, i):
    N = len(acc_df)

    print("="*70)
    print(f"[PEAK DEBUG] index={i}, time={acc_df.iloc[i]['Time']}")
    print("="*70)

              
    if i < WIN_L or i >= N - WIN_R:
        print("❌ Boundary fail (window out of range)")
        return

    mag = acc_df.iloc[i]["mag_g"]
    base = acc_df.iloc[i]["baseline_g"]
    amp  = acc_df.iloc[i]["amp_g"]

    print(f"mag_g      = {mag:.4f} g")
    print(f"baseline_g = {base:.4f} g")
    print(f"amplitude  = {amp:.4f} g")

                   
    l_vals = acc_df.iloc[i-PEAK_CHECK_LEFT:i]["mag_g"].values
    r_vals = acc_df.iloc[i+1:i+1+PEAK_CHECK_RIGHT]["mag_g"].values
    is_local_max = mag >= max(l_vals) and mag >= max(r_vals)

    print(f"\n[STEP 1] Local max")
    print(f" left : {l_vals}")
    print(f" right: {r_vals}")
    print(f" -> pass = {is_local_max}")

                   
    pass_amp = amp is not None and amp >= PROM_THRESH_G
    print(f"\n[STEP 2] Amplitude check")
    print(f" threshold = {PROM_THRESH_G} g")
    print(f" -> pass = {pass_amp}")

                       
    avgL = acc_df.iloc[i-WIN_L:i]["mag_g"].mean()
    avgR = acc_df.iloc[i+1:i+1+WIN_R]["mag_g"].mean()
    pass_avg = avgL >= AVG_MAG_THRESH_G and avgR >= AVG_MAG_THRESH_G

    print(f"\n[STEP 3] Avg magnitude")
    print(f" avgL={avgL:.4f}, avgR={avgR:.4f}")
    print(f" threshold={AVG_MAG_THRESH_G}")
    print(f" -> pass = {pass_avg}")

    is_peak = is_local_max and pass_amp and pass_avg
    print(f"\n[FINAL] is_peak = {is_peak}")


                                                                                                              
                                  
 
LOG_COND3 = True
LOG_COND4 = True
LOG_COND5 = True
                                                                     
                               
                                                                     
def ffh_cond1_strong(peaks_df, mag_th=5.0, amp_th=1.0):
    df = peaks_df[
        (peaks_df["mag_g_peak"] >= mag_th) &
        (peaks_df["prom_g"] >= amp_th)
    ].copy()

    print(f"======================= [COND1] strong peaks = {len(df)} =======================")
    return df
                                                                     
                                     
                                                                     
def ffh_cond2_window(df, acc_df, win=40):
    valid = []

    for _, r in df.iterrows():
        i = r["index"]
        if i - win >= 0 and i + win < len(acc_df):
            valid.append(r)

    df2 = pd.DataFrame(valid)
    print(f"======================= [COND2] window-valid peaks = {len(df2)} =======================")
    return df2

                                                                     
 
                                                                     
def _idx_to_time(acc_df, idx):
    return acc_df.iloc[int(idx)]["Time"]

                                                                     
                      
                                                                     
def ffh_cond3_pre_peak(df, all_peaks_df, lookback=40):
    if df.empty:
        return pd.DataFrame(columns=list(df.columns) + [
            "cond3_pass",
            "cond3_reason"
        ])
    
    rows = []

    for _, r in df.iterrows():
        i = int(r["index"])
        cur_mag = r["mag_g_peak"]

        pre = all_peaks_df[
            (all_peaks_df["index"] < i) &
            (all_peaks_df["index"] >= i - lookback) &
            (all_peaks_df["mag_g_peak"] < cur_mag)
        ]

        t = acc_df.iloc[i]["Time"]              

        print(
            f"[COND3] idx={i} | time={t} | "
            f"mag={cur_mag:.2f}g | pre_peak_cnt={len(pre)}"
        )
        r2 = r.copy()

        if len(pre) > 0:
            r2["cond3_pass"] = True
            r2["cond3_reason"] = "ok"
        else:
            r2["cond3_pass"] = False
            r2["cond3_reason"] = "no smaller pre-peak in lookback"
            print("        ❌ no smaller pre-peak")
             
        rows.append(r2)

    df_out = pd.DataFrame(rows)
                            
    if df_out.empty:
        return df.iloc[0:0].copy()

    if "cond3_pass" not in df_out.columns:
        df_out["cond3_pass"] = False

    print(
        f"======================= "
        f"[COND3] pass={df_out['cond3_pass'].sum()} / total={len(df_out)} "
        f"======================="
    )

    print(f"======================= [COND3] pass={df_out['cond3_pass'].sum()} / total={len(df_out)} =======================")
    return df_out

                                                                     
                                    
                                                                     
def ffh_cond4_post_stable(
    df,
    acc_df,
    window_size=10,
    n_windows=5,
    min_consecutive=3
):
    
    if df.empty:
        return pd.DataFrame(columns=list(df.columns) + [
            "cond4",
            "stable_cnt",
            "cond4_reason"
        ])
    rows = []

    for _, r in df.iterrows():
        i = int(r["index"])
        t = acc_df.iloc[i]["Time"]

        segments = []
        stable_flags = []

                                   
                   
                                   
        for k in range(n_windows):
            start = i + 1 + k * window_size
            end   = i + 1 + (k + 1) * window_size

            if end > len(acc_df):
                segments.append({
                    "window_idx": k,
                    "start_idx": start,
                    "end_idx": end,
                    "mean_g": None,
                    "is_stable": False,
                    "reason": "out_of_range"
                })
                stable_flags.append(False)
                continue

            seg = acc_df.iloc[start:end]
            mean_g = seg["mag_g"].mean()

            is_stable = (0.85 <= mean_g <= 1.2)

            segments.append({
                "window_idx": k,
                "start_idx": start,
                "end_idx": end,
                "mean_g": mean_g,
                "is_stable": is_stable,
                "reason": "ok" if is_stable else "mean_out_of_range"
            })

            stable_flags.append(is_stable)

                                   
                       
                                   
        max_consecutive = 0
        current_run = 0

        for flag in stable_flags:
            if flag:
                current_run += 1
                max_consecutive = max(max_consecutive, current_run)
            else:
                current_run = 0

        cond4_pass = max_consecutive >= min_consecutive

                                   
               
                                   
        r2 = r.copy()
        r2["post_segments"] = segments
        r2["max_consecutive_stable"] = max_consecutive
        r2["cond4"] = cond4_pass

        if cond4_pass:
            r2["cond4_reason"] = f"{max_consecutive} consecutive stable"
        else:
            if max_consecutive == 2:
                r2["cond4_reason"] = "only 2 consecutive stable"
            elif max_consecutive == 1:
                r2["cond4_reason"] = "only 1 consecutive stable"
            else:
                r2["cond4_reason"] = "no stable segment"

        rows.append(r2)

        print(
            f"[COND4] idx={i:6d} | "
            f"max_consecutive={max_consecutive} | "
            f"{'PASS' if cond4_pass else 'FAIL'}"
        )

    df4 = pd.DataFrame(rows)
                  
    if df4.empty:
        print("[COND4] no data passed from cond3")
        return df4

    if "cond4" not in df4.columns:
        df4["cond4"] = False

    print(
        f"======================= [COND4] "
        f"total={len(df4)}, pass={df4['cond4'].sum()}"
    )

    return df4

                                                                     
                              
                                                                     
def ffh_cond5_pressure(
    df,
    acc_df,
    env_df,
    drop_m=1.0,
    sec_range=2
):
    
    if df.empty:
        return pd.DataFrame(columns=list(df.columns) + [
            "cond5",
            "pressure_dp_hpa",
            "height_drop_m",
            "pressure_dir",
            "cond5_reason"
        ])
    rows = []
    dp_th = drop_m / 8.3

    for _, r in df.iterrows():
        r2 = r.copy()
        i = int(r2["index"])
        t0 = acc_df.iloc[i]["Time"]

        win = env_df[
            (env_df["Time"] >= t0 - timedelta(seconds=sec_range)) &
            (env_df["Time"] <= t0 + timedelta(seconds=sec_range))
        ].sort_values("Time")

                                   
        best_sum = 0.0
        h_drop = 0.0
        r2["cond5"] = False
        r2["pressure_dp_hpa"] = 0.0
        r2["height_drop_m"] = 0.0
        r2["pressure_dir"] = None
        r2["cond5_reason"] = "init"

                                          
        if len(win) < 3:
            r2["cond5_reason"] = "not_enough_env_samples"
        else:
            pressures = win["Pressure (hPa)"].values
            dps = [pressures[j+1] - pressures[j]
                   for j in range(len(pressures)-1)]
            dps = [dp for dp in dps if dp != 0]

            if not dps:
                r2["cond5_reason"] = "no_pressure_change"
            else:
                        
                cur_sum = dps[0]
                cur_sign = 1 if dps[0] > 0 else -1
                best_sum = cur_sum

                for dp in dps[1:]:
                    sign = 1 if dp > 0 else -1
                    if sign == cur_sign:
                        cur_sum += dp
                    else:
                        if abs(cur_sum) > abs(best_sum):
                            best_sum = cur_sum
                        cur_sum = dp
                        cur_sign = sign

                if abs(cur_sum) > abs(best_sum):
                    best_sum = cur_sum

                h_drop = abs(best_sum) * 8.3

                r2["pressure_dp_hpa"] = best_sum
                r2["height_drop_m"] = h_drop
                r2["pressure_dir"] = "increase" if best_sum > 0 else "decrease"

                if h_drop >= drop_m:
                    r2["cond5"] = True
                    r2["cond5_reason"] = "ok"
                else:
                    r2["cond5_reason"] = (
                        f"height_drop={h_drop:.2f}m < {drop_m:.2f}m"
                    )

        rows.append(r2)

                                      
        print(
            f"{'[COND5] PASS' if r2['cond5'] else '        ❌ FAIL'} | "
            f"idx={i:6d} | "
            f"ΔP_sum={best_sum:+.3f} hPa | "
            f"Δh={h_drop:.2f} m | "
            f"dir={'inc' if best_sum > 0 else 'dec'} | "
            
            f"reason={r2['cond5_reason']}"
        )

    df5 = pd.DataFrame(rows)
    df5 = pd.DataFrame(rows)

    if df5.empty:
        print("[COND5] empty result")
        return df5

    print(
        f"======================= [COND5] total={len(df5)}, "
        f"pass={df5['cond5'].sum()}, "
        f"fail={(~df5['cond5']).sum()} ======================="
    )
    return df5

    rows = []

    for _, r in peaks_df.iterrows():
        idx = int(r["index"])
        t   = acc_df.iloc[idx]["Time"]

        row = {
                   
            "index": idx,
            "Time": t,

                     
            "peak_mag_g": r["mag_g_peak"],
            "peak_amp_g": r["prom_g"],
        }

                           
               
                           
        row["cond3"] = check_cond3_pre_peak_single(
            r, peaks_df
        )

                           
               
                           
        cond4_ok, stable_cnt = check_cond4_single(
            r, acc_df
        )
        row["cond4"] = cond4_ok
        row["cond4_stable_cnt"] = stable_cnt

                           
               
                           
        cond5_ok, h_drop, dp_hpa = check_cond5_single(
            r, acc_df, env_df
        )
        row["cond5"] = cond5_ok
        row["cond5_height_m"] = h_drop
        row["cond5_dp_hpa"] = dp_hpa

                           
               
                           
        row["P_fall"] = (
            0.25 * row["cond3"] +
            0.25 * row["cond4"] +
            0.50 * row["cond5"]
        )

        rows.append(row)

    return pd.DataFrame(rows)

                                                                     
  
                                                                     
import plotly.express as px

                                                         

                  
                
                
               
   

            
                                                                     
                   
                                                                     
def safe_filter(df, flag):

    if df is None:
        return pd.DataFrame(columns=["index"])

    if flag not in df.columns:
        return pd.DataFrame(columns=["index"])

    if df.empty:
        return pd.DataFrame(columns=["index"])

    return df[df[flag]][["index"]]
                                                                     
  
                                                                     

                                                                     
  
                                                                     

                                                                     
  
                                                                     

                                                                     
  
                                                                     

                                                                     
  
                                                                     

