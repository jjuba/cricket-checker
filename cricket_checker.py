"""
=============================================================
  🏏 T20 CRICKET LIVE CONDITION CHECKER + TELEGRAM ALERT
=============================================================
শর্তসমূহ (যেকোনো ১টা সত্যি হলেই Telegram এ মেসেজ যাবে):
  1.  1st Over High Score (1st Innings >= 14)
  2.  1st Over High Score (2nd Innings >= 13)
  3.  16 Over 4 Wkt (2nd Innings)
  4.  Catch Drop (2nd Innings till 2 Overs)
  5.  Clear Table Topper (2nd Bat)
  6.  Clear Table Bottom (1st Bat)
  7.  Home Team 6 Over No Loss (1st Bat)
  8.  Wicket Keeper Not Out (1st Innings)
  9.  Shortened Game (Rain)
=============================================================
"""

import requests
import time
import os
from datetime import datetime

# =============================================
#   ⚙️  কনফিগারেশন (Railway Variables থেকে আসবে)
# =============================================
RAPIDAPI_KEY     = os.environ.get("RAPIDAPI_KEY")
RAPIDAPI_HOST    = "cricbuzz-cricket.p.rapidapi.com"
TELEGRAM_TOKEN   = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
POLL_INTERVAL    = 1800  # 45 মিনিট

HEADERS = {
    "X-RapidAPI-Key": RAPIDAPI_KEY,
    "X-RapidAPI-Host": RAPIDAPI_HOST
}

# duplicate নোটিফিকেশন আটকাতে
notified_conditions = set()


# =============================================
#   📨  TELEGRAM ফাংশন
# =============================================

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }
    try:
        res = requests.post(url, json=payload, timeout=10)
        if res.status_code == 200:
            print("  📨 Telegram মেসেজ পাঠানো হয়েছে!")
        else:
            print(f"  [Telegram ERROR] {res.text}")
    except Exception as e:
        print(f"  [Telegram ERROR] {e}")


# =============================================
#   📡  API ফাংশন
# =============================================

def api_get(url):
    try:
        res = requests.get(url, headers=HEADERS, timeout=10)
        res.raise_for_status()
        return res.json()
    except Exception as e:
        print(f"  [API ERROR] {url.split('/')[-1]}: {e}")
        return None

def get_live_matches():
    return api_get("https://cricbuzz-cricket.p.rapidapi.com/matches/v1/live")

def get_scorecard(match_id):
    return api_get(f"https://cricbuzz-cricket.p.rapidapi.com/mcenter/v1/{match_id}/scard")

def get_match_info(match_id):
    return api_get(f"https://cricbuzz-cricket.p.rapidapi.com/mcenter/v1/{match_id}")

def get_standings(series_id):
    return api_get(f"https://cricbuzz-cricket.p.rapidapi.com/series/v1/{series_id}/standings")

def get_commentary(match_id):
    return api_get(f"https://cricbuzz-cricket.p.rapidapi.com/mcenter/v1/{match_id}/comm")


# =============================================
#   🔧  হেল্পার ফাংশন
# =============================================

def parse_innings(scorecard):
    innings_list = []
    try:
        for inn in scorecard.get("scoreCard", []):
            innings_list.append({
                "innings_id":   inn.get("inningsId", 0),
                "team_name":    inn.get("batTeamDetails", {}).get("batTeamName", "Unknown"),
                "team_id":      inn.get("batTeamDetails", {}).get("batTeamId", 0),
                "runs":         inn.get("scoreDetails", {}).get("runs", 0),
                "wickets":      inn.get("scoreDetails", {}).get("wickets", 0),
                "overs":        float(inn.get("scoreDetails", {}).get("overs", 0)),
                "bat_details":  inn.get("batTeamDetails", {}).get("batsmenData", {}),
                "over_summary": inn.get("overSummary", []),
            })
    except Exception as e:
        print(f"  [PARSE ERROR] {e}")
    return innings_list

def first_over_runs(inn):
    for ov in inn.get("over_summary", []):
        if ov.get("overNum") == 1:
            return ov.get("runs", 0)
    return None

def get_inn(innings_list, inn_id):
    for inn in innings_list:
        if inn["innings_id"] == inn_id:
            return inn
    return None

def status_icon(val):
    if val is True:  return "✅ পাস"
    if val is False: return "❌ ফেল"
    return "⏳ অপেক্ষা"


# =============================================
#   🔍  ৯টি শর্ত চেকার
# =============================================

def cond1(innings_list):
    inn = get_inn(innings_list, 1)
    if inn and inn["overs"] >= 1.0:
        runs = first_over_runs(inn)
        if runs is not None:
            ok = runs >= 14
            return ok, f"১ম ইনিংসের ১ম ওভারে {runs} রান {'✅ >= 14' if ok else '❌ < 14'}"
    return None, "১ম ইনিংসের ১ম ওভার শেষ হয়নি"

def cond2(innings_list):
    inn = get_inn(innings_list, 2)
    if inn and inn["overs"] >= 1.0:
        runs = first_over_runs(inn)
        if runs is not None:
            ok = runs >= 13
            return ok, f"২য় ইনিংসের ১ম ওভারে {runs} রান {'✅ >= 13' if ok else '❌ < 13'}"
    return None, "২য় ইনিংস শুরু হয়নি বা ১ম ওভার শেষ হয়নি"

def cond3(innings_list):
    inn = get_inn(innings_list, 2)
    if inn and inn["overs"] >= 16.0:
        ok = inn["wickets"] >= 4
        return ok, f"২য় ইনিংস ১৬ ওভারে {inn['wickets']} উইকেট {'✅ >= 4' if ok else '❌ < 4'}"
    return None, "২য় ইনিংস এখনো ১৬ ওভার হয়নি"

def cond4(commentary_data):
    if not commentary_data:
        return None, "কমেন্ট্রি ডেটা নেই"
    try:
        for comm in commentary_data.get("commentaryList", []):
            if comm.get("inningsId") == 2 and comm.get("overNum", 99) <= 2:
                text = comm.get("commText", "").lower()
                if any(w in text for w in ["drop", "dropped", "missed catch"]):
                    return True, f"ওভার {comm.get('overNum')}: ক্যাচ ড্রপ ✅"
        return False, "২য় ইনিংসের প্রথম ২ ওভারে ক্যাচ ড্রপ নেই ❌"
    except Exception as e:
        return None, f"চেক করতে সমস্যা: {e}"

def cond5_6(innings_list, standings_data):
    r5 = (None, "স্ট্যান্ডিংস ডেটা নেই")
    r6 = (None, "স্ট্যান্ডিংস ডেটা নেই")
    inn1 = get_inn(innings_list, 1)
    inn2 = get_inn(innings_list, 2)
    if not standings_data or not inn1:
        return r5, r6
    try:
        for td in standings_data.get("standings", {}).get("standings", []):
            tid    = td.get("teamId")
            played = td.get("matchesPlayed", 0)
            wins   = td.get("matchesWon", 0)
            losses = td.get("matchesLost", 0)
            if inn2 and tid == inn2["team_id"]:
                ok = played >= 2 and losses == 0
                r5 = (ok, f"{inn2['team_name']}: {played} ম্যাচ, {losses} হার {'✅ Clear Topper' if ok else '❌ Not Topper'}")
            if inn1 and tid == inn1["team_id"]:
                ok = played >= 2 and wins == 0
                r6 = (ok, f"{inn1['team_name']}: {played} ম্যাচ, {wins} জয় {'✅ Clear Bottom' if ok else '❌ Not Bottom'}")
    except Exception as e:
        r5 = (None, f"এরর: {e}")
        r6 = (None, f"এরর: {e}")
    return r5, r6

def cond7(innings_list, match_info):
    try:
        home_id = match_info.get("matchInfo", {}).get("team1", {}).get("teamId")
        inn1 = get_inn(innings_list, 1)
        if inn1 and inn1["team_id"] == home_id:
            if inn1["overs"] >= 6.0:
                ok = inn1["wickets"] == 0
                return ok, f"হোম টিম ৬ ওভারে {inn1['wickets']} উইকেট {'✅ No Loss' if ok else '❌ উইকেট পড়েছে'}"
            return None, f"হোম টিম ব্যাট করছে, এখন {inn1['overs']} ওভার"
        return None, "হোম টিম প্রথমে ব্যাট করছে না"
    except Exception as e:
        return None, f"এরর: {e}"

def cond8(innings_list):
    inn1 = get_inn(innings_list, 1)
    if not inn1 or inn1["overs"] < 1.0:
        return None, "১ম ইনিংস শুরু হয়নি"
    try:
        for _, player in inn1["bat_details"].items():
            name = player.get("batName", "")
            if "(wk)" in name.lower() or "†" in name or player.get("isKeeper", False):
                out_desc = player.get("outDesc", "").lower()
                not_out = out_desc == "" or "not out" in out_desc or "batting" in out_desc
                return not_out, f"WK {name} {'আউট হননি ✅' if not_out else 'আউট হয়ে গেছেন ❌'}"
        return None, "উইকেটরক্ষক শনাক্ত করা যায়নি"
    except Exception as e:
        return None, f"এরর: {e}"

def cond9(match_info):
    try:
        status = match_info.get("matchInfo", {}).get("status", "").lower()
        desc   = match_info.get("matchInfo", {}).get("matchDesc", "").lower()
        rain_kw = ["rain", "d/l", "duckworth", "weather", "wet", "abandoned", "reduced"]
        ok = any(kw in status or kw in desc for kw in rain_kw)
        return ok, f"স্ট্যাটাস: {match_info.get('matchInfo', {}).get('status', 'N/A')} {'✅ Rain/D-L' if ok else '❌ বৃষ্টি নেই'}"
    except Exception as e:
        return None, f"এরর: {e}"


# =============================================
#   🖨️  ডিসপ্লে
# =============================================

CONDITION_NAMES = [
    "1st Over High Score (1st Inns >= 14)",
    "1st Over High Score (2nd Inns >= 13)",
    "16 Over 4 Wkt (2nd Inns)",
    "Catch Drop (2nd Inns till 2 Overs)",
    "Clear Table Topper (2nd Bat)",
    "Clear Table Bottom (1st Bat)",
    "Home Team 6 Over No Loss (1st Bat)",
    "Wicket Keeper Not Out (1st Inns)",
    "Shortened Game (Rain)",
]


# =============================================
#   🚀  মেইন লুপ
# =============================================

def run():
    print("✅ সব লাইভ T20 ম্যাচ অটো চেক শুরু হয়েছে...")
    while True:
        try:
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            print(f"\n{'='*55}")
            print(f"  ⏰ চেক শুরু: {now}")
            print(f"{'='*55}")

            live_data = get_live_matches()
            if not live_data:
                print("  ⚠️ লাইভ ডেটা আনা যায়নি, আবার চেষ্টা হবে...")
                time.sleep(POLL_INTERVAL)
                continue

            # সব T20 ম্যাচ বের করো
            t20_matches = []
            for type_match in live_data.get("typeMatches", []):
                for series in type_match.get("seriesMatches", []):
                    wrapper = series.get("seriesAdWrapper", {})
                    for match in wrapper.get("matches", []):
                        mi = match.get("matchInfo", {})
                        if mi.get("matchFormat", "").upper() == "T20":
                            t20_matches.append({
                                "id":        mi.get("matchId"),
                                "series_id": mi.get("seriesId"),
                                "name":      f"{mi.get('team1',{}).get('teamName','?')} vs {mi.get('team2',{}).get('teamName','?')}",
                            })

            if not t20_matches:
                print("  ⚠️ এই মুহূর্তে কোনো লাইভ T20 ম্যাচ নেই।")
                print(f"  🔄 {POLL_INTERVAL} সেকেন্ড পর আবার চেক হবে...")
                time.sleep(POLL_INTERVAL)
                continue

            print(f"  📺 {len(t20_matches)}টি লাইভ T20 ম্যাচ পাওয়া গেছে।")

            # প্রতিটা ম্যাচ চেক করো
            for match in t20_matches:
                match_id   = match["id"]
                series_id  = match["series_id"]
                match_name = match["name"]

                print(f"\n  🏏 [{match_name}] চেক হচ্ছে...")

                scorecard      = get_scorecard(match_id)
                match_info     = get_match_info(match_id)
                standings_data = get_standings(series_id) if series_id else None
                commentary     = get_commentary(match_id)

                if not scorecard or not match_info:
                    print("  ⚠️ ডেটা আনা যায়নি, এই ম্যাচ স্কিপ হচ্ছে।")
                    continue

                innings_list = parse_innings(scorecard)
                inn2       = get_inn(innings_list, 2)
                team2_name = inn2["team_name"] if inn2 else "২য় টিম"

                score_parts = [
                    f"{i['team_name']}: {i['runs']}/{i['wickets']} ({i['overs']} ov)"
                    for i in innings_list
                ]
                score = "  |  ".join(score_parts) or "ডেটা নেই"

                r5, r6 = cond5_6(innings_list, standings_data)
                results = [
                    cond1(innings_list),
                    cond2(innings_list),
                    cond3(innings_list),
                    cond4(commentary),
                    r5,
                    r6,
                    cond7(innings_list, match_info),
                    cond8(innings_list),
                    cond9(match_info),
                ]

                # ফলাফল প্রিন্ট ও Telegram অ্যালার্ট
                for i, (name, (val, detail)) in enumerate(zip(CONDITION_NAMES, results)):
                    print(f"    {i+1}. [{status_icon(val)}] {name}")
                    print(f"         └─ {detail}")

                    notif_key = f"{match_id}_{i}"
                    if val is True and notif_key not in notified_conditions:
                        notified_conditions.add(notif_key)
                        msg = (
                            f"🏏 <b>T20 CRICKET ALERT</b>\n"
                            f"━━━━━━━━━━━━━━━━━━━━\n"
                            f"📍 <b>ম্যাচ:</b> {match_name}\n"
                            f"📊 <b>স্কোর:</b> {score}\n"
                            f"━━━━━━━━━━━━━━━━━━━━\n"
                            f"✅ <b>পূরণ হওয়া শর্ত:</b>\n"
                            f"   🔸 {name}\n"
                            f"   └─ {detail}\n"
                            f"━━━━━━━━━━━━━━━━━━━━\n"
                            f"🎯 <b>{team2_name} জিততে পারে!</b>\n"
                            f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                        )
                        send_telegram(msg)

            print(f"\n  🔄 পরবর্তী চেক: {POLL_INTERVAL} সেকেন্ড পর...")
            time.sleep(POLL_INTERVAL)

        except KeyboardInterrupt:
            print("\n  👋 প্রোগ্রাম বন্ধ।")
            break
        except Exception as e:
            print(f"  [ERROR] {e}")
            time.sleep(POLL_INTERVAL)


def main():
    print("=" * 55)
    print("  🏏  T20 CRICKET LIVE CONDITION CHECKER")
    print("  Cricbuzz (RapidAPI) + Telegram Alert")
    print("=" * 55)

    # কনফিগ চেক
    errors = []
    if not RAPIDAPI_KEY:     errors.append("RAPIDAPI_KEY")
    if not TELEGRAM_TOKEN:   errors.append("TELEGRAM_TOKEN")
    if not TELEGRAM_CHAT_ID: errors.append("TELEGRAM_CHAT_ID")

    if errors:
        print(f"\n  ⚠️  Railway Variables এ নেই: {', '.join(errors)}")
        print("  Railway → আপনার Project → Variables এ বসান।\n")
        return

    run()


if __name__ == "__main__":
    main()
