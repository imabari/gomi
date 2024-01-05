import pathlib
import datetime

import pandas as pd
from ics import Calendar, Event


# ごみカレンダーを生成
def gomi_calendar(area, df):
    c = Calendar()
    c.serializecreator = "今治市"

    for _, row in df.iterrows():
        event = Event()
        event.name = row["ごみ"]
        event.begin = row["開始"]
        event.end = row["終了"]

        c.events.add(event)

    p = pathlib.Path("calendar", f"{area}.ics")
    p.parent.mkdir(parents=True, exist_ok=True)

    with open(p, "w", encoding="utf-8") as f:
        f.write(c.serialize())


# 今日
JST = datetime.timezone(datetime.timedelta(hours=+9))
dt_now = datetime.datetime.now(JST).replace(tzinfo=None)

# 年度
year = dt_now.year - int(dt_now.month < 4)

# 年度の日付生成
date_index = pd.date_range(start=f"{year}-04-01", end=f"{year + 1}-03-31", freq="D")
df_date = pd.DataFrame(index=date_index)

# 正月三が日
dates_to_remove = [f"{year + 1}-01-01", f"{year + 1}-01-02", f"{year + 1}-01-03"]

# 正月三が日を削除
df_date = df_date.drop(dates_to_remove, axis=0, errors="ignore")

# 曜日名辞書生成
weekday = {i: v for i, v in enumerate("月火水木金土日")}

# 週目
df_date["week_number"] = (df_date.index.day - 1) // 7 + 1

# 曜日
df_date["weekday"] = df_date.index.weekday
df_date["week_name"] = df_date["weekday"].apply(lambda x: weekday[x])

# 曜日パターン生成
days = {}

for 曜日 in "月火水木金土日":
    days[f"第１・３{曜日}"] = df_date[
        df_date["week_number"].isin([1, 3]) & (df_date["week_name"] == 曜日)
    ].index

    days[f"第２・４{曜日}"] = df_date[
        df_date["week_number"].isin([2, 4]) & (df_date["week_name"] == 曜日)
    ].index

    days[曜日] = df_date[df_date["week_name"] == 曜日].index

# 今治市ごみ収集日一覧表
df_area = pd.read_csv("imabari_gomi.csv", index_col=0)

for area, row in df_area.iterrows():
    # ごみ種類ごとの日付生成
    data = [pd.Series("可燃", index=days[i]) for i in row["可燃"].split("・")]

    data.append(pd.Series("不燃", index=days[row["不燃"]]))
    data.append(pd.Series("プラ", index=days[row["プラ"]]))
    data.append(pd.Series("資源", index=days[row["資源"]]))

    # ごみ種類別をひとつに結合
    sr = pd.concat(data)

    # ごみの種類ごとに横に並べる
    df0 = (
        sr.reset_index(name="value")
        .pivot(index="index", columns="value", values="value")
        .reindex(columns=["可燃", "不燃", "プラ", "資源"])
    )

    # 同日はごみ種類を結合
    df1 = df0.apply(lambda s: "・".join(s.dropna()), axis=1).to_frame(name="ごみ")

    # タイムゾーンを日本に設定
    df1["開始"] = (df1.index + pd.Timedelta("8:30:00")).tz_localize("Asia/Tokyo")
    df1["終了"] = (df1.index + pd.Timedelta("9:00:00")).tz_localize("Asia/Tokyo")

    gomi_calendar(area, df1)
