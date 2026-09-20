# -*- coding: utf-8 -*-
"""
🏸 ỨNG DỤNG QUẢN LÝ HOST SÂN CẦU LÔNG (Single-Page, Mobile First)
Chạy bằng: streamlit run app.py
Dành cho 1 người dùng thao tác, dữ liệu lưu tạm trong st.session_state (mất khi tắt trình duyệt/server).
"""

import streamlit as st
import itertools
import random

# =========================================================================
# 0. CẤU HÌNH TRANG - tối ưu cho điện thoại (dọc, gọn)
# =========================================================================
st.set_page_config(
    page_title="Quản lý Sân Cầu Lông",
    page_icon="🏸",
    layout="centered",          # co gọn giữa màn hình -> chuẩn mobile
    initial_sidebar_state="collapsed",
)

# CSS tinh chỉnh cho gọn hơn trên điện thoại: giảm padding, thu nhỏ nút, ...
st.markdown(
    """
    <style>
    .block-container {padding-top: 1rem; padding-bottom: 3rem; padding-left: 0.8rem; padding-right: 0.8rem;}
    div[data-testid="stMetric"] {background:#f6f6f8; padding:6px 8px; border-radius:10px;}
    div[data-testid="stMetricValue"] {font-size: 1.1rem;}
    div[data-testid="stMetricLabel"] {font-size: 0.72rem;}
    .stButton>button {padding: 0.25rem 0.5rem; font-size: 0.85rem;}
    hr {margin: 0.4rem 0;}
    .player-card {border:1px solid #e6e6e6; border-radius:10px; padding:6px 10px; margin-bottom:6px;}
    .small-note {font-size:0.75rem; color:#888;}
    </style>
    """,
    unsafe_allow_html=True,
)

# =========================================================================
# 1. HẰNG SỐ & DANH MỤC LỰA CHỌN
# =========================================================================
LEVEL_MAP = {"🔴 Mạnh": 3, "🟡 Bình thường": 2, "🔵 Yếu": 1}       # dùng để tính cân kèo
LEVEL_OPTIONS = list(LEVEL_MAP.keys())
GENDER_OPTIONS = ["♂️ Nam", "♀️ Nữ"]
GUEST_OPTIONS = ["Quen", "Vãng lai"]
MAX_PLAYERS = 16

# =========================================================================
# 2. KHỞI TẠO SESSION STATE
# =========================================================================
if "players" not in st.session_state:
    st.session_state.players = []          # list[dict]
if "next_id" not in st.session_state:
    st.session_state.next_id = 1
if "court1" not in st.session_state:
    st.session_state.court1 = []           # list các player id đang ở Sân 1
if "court2" not in st.session_state:
    st.session_state.court2 = []
if "pair_history" not in st.session_state:
    st.session_state.pair_history = {}     # {(id1,id2): số lần ĐÃ CẶP CÙNG ĐỘI}
if "opp_history" not in st.session_state:
    st.session_state.opp_history = {}      # {(id1,id2): số lần ĐÃ ĐỐI ĐẦU}
if "suggestion1" not in st.session_state:
    st.session_state.suggestion1 = None    # gợi ý đang chờ xác nhận cho Sân 1
if "suggestion2" not in st.session_state:
    st.session_state.suggestion2 = None


# =========================================================================
# 3. CÁC HÀM XỬ LÝ DỮ LIỆU / THUẬT TOÁN
# =========================================================================
def get_player(pid):
    """Lấy player dict theo id."""
    for p in st.session_state.players:
        if p["id"] == pid:
            return p
    return None


def pkey(a, b):
    """Key không phân biệt thứ tự cho 1 cặp id."""
    return tuple(sorted([a, b]))


def add_player(name, gender, guest_type, level, appearance):
    """Thêm khách mới vào danh sách chờ."""
    st.session_state.players.append(
        {
            "id": st.session_state.next_id,
            "name": name.strip(),
            "gender": gender,
            "guest_type": guest_type,
            "level": level,
            "appearance": appearance.strip(),
            "matches": 0,
            "checked_in": False,
            "payment": "Chưa thu",
            "on_court": None,   # None / 1 / 2
        }
    )
    st.session_state.next_id += 1


def get_waiting_players():
    """Người đã check-in, hiện KHÔNG ở trên sân nào -> đang chờ."""
    return [p for p in st.session_state.players if p["checked_in"] and p["on_court"] is None]


def score_pairing(combo):
    """
    Với 4 người (combo), thử cả 3 cách chia 2 đội -> chọn cách chia
    có điểm phạt (trùng lặp lịch sử + lệch trình độ) THẤP NHẤT.
    Trả về (score, pairing, repeat_count, balance_diff)
    """
    best = None
    splits = [
        ((combo[0], combo[1]), (combo[2], combo[3])),
        ((combo[0], combo[2]), (combo[1], combo[3])),
        ((combo[0], combo[3]), (combo[1], combo[2])),
    ]
    for (p1, p2), (p3, p4) in splits:
        # Phạt nặng nếu 2 người từng CẶP CÙNG ĐỘI với nhau
        repeat = (
            st.session_state.pair_history.get(pkey(p1, p2), 0)
            + st.session_state.pair_history.get(pkey(p3, p4), 0)
        )
        # Phạt nhẹ hơn nếu từng ĐỐI ĐẦU nhau
        repeat += (
            st.session_state.opp_history.get(pkey(p1, p3), 0)
            + st.session_state.opp_history.get(pkey(p1, p4), 0)
            + st.session_state.opp_history.get(pkey(p2, p3), 0)
            + st.session_state.opp_history.get(pkey(p2, p4), 0)
        )
        lvl = lambda pid: LEVEL_MAP[get_player(pid)["level"]]
        balance = abs((lvl(p1) + lvl(p2)) - (lvl(p3) + lvl(p4)))
        # Trọng số: ưu tiên tránh trùng lặp (x10) hơn là cân kèo tuyệt đối
        total_score = repeat * 10 + balance
        if best is None or total_score < best[0]:
            best = (total_score, ((p1, p2), (p3, p4)), repeat, balance)
    return best


def suggest_court():
    """
    Thuật toán gợi ý:
    1. Lấy danh sách đang chờ (đã đến, chưa vào sân).
    2. Ưu tiên nhóm có SỐ TRẬN ÍT NHẤT (lấy 1 buffer nhỏ để có nhiều lựa chọn).
    3. Duyệt mọi tổ hợp 4 người trong nhóm ưu tiên -> chọn tổ hợp + cách chia đội
       có điểm phạt thấp nhất (ít lặp lịch sử nhất, cân trình độ nhất).
    """
    waiting = get_waiting_players()
    if len(waiting) < 4:
        return None

    waiting_sorted = sorted(waiting, key=lambda p: p["matches"])
    min_matches = waiting_sorted[0]["matches"]
    # Lấy nhóm ưu tiên: số trận thấp nhất hoặc thấp hơn +1 (để có đủ người so sánh)
    pool = [p for p in waiting_sorted if p["matches"] <= min_matches + 1]
    if len(pool) < 4:
        pool = waiting_sorted[:max(8, 4)]
    pool = pool[:10]  # giới hạn để số tổ hợp không quá lớn (C(10,4)=210)

    ids = [p["id"] for p in pool]
    best_overall = None
    for combo in itertools.combinations(ids, 4):
        score, pairing, repeat, balance = score_pairing(list(combo))
        if best_overall is None or score < best_overall[0]:
            best_overall = (score, combo, pairing, repeat, balance)
    return best_overall  # (score, combo_ids(4), pairing, repeat, balance)


def confirm_to_court(court_num, player_ids, pairing=None):
    """
    Xác nhận 4 người vào sân:
    - Gán on_court, cộng +1 trận cho mỗi người.
    - Lưu lịch sử cặp/đối đầu (nếu có pairing cụ thể từ gợi ý tự động;
      nếu là thủ công thì mặc định chia theo thứ tự chọn: 2 người đầu 1 đội, 2 người sau 1 đội).
    """
    court_key = f"court{court_num}"
    st.session_state[court_key] = list(player_ids)
    for pid in player_ids:
        p = get_player(pid)
        p["matches"] += 1
        p["on_court"] = court_num

    if pairing is None:
        p1, p2, p3, p4 = player_ids
        pairing = ((p1, p2), (p3, p4))
    (p1, p2), (p3, p4) = pairing

    # Lưu lịch sử cặp cùng đội
    st.session_state.pair_history[pkey(p1, p2)] = st.session_state.pair_history.get(pkey(p1, p2), 0) + 1
    st.session_state.pair_history[pkey(p3, p4)] = st.session_state.pair_history.get(pkey(p3, p4), 0) + 1
    # Lưu lịch sử đối đầu
    for a, b in [(p1, p3), (p1, p4), (p2, p3), (p2, p4)]:
        st.session_state.opp_history[pkey(a, b)] = st.session_state.opp_history.get(pkey(a, b), 0) + 1


def end_match(court_num):
    """Kết thúc trận trên 1 sân -> trả người chơi về trạng thái chờ."""
    court_key = f"court{court_num}"
    for pid in st.session_state[court_key]:
        p = get_player(pid)
        if p:
            p["on_court"] = None
    st.session_state[court_key] = []
    st.session_state[f"suggestion{court_num}"] = None


# =========================================================================
# 4. GIAO DIỆN - TIÊU ĐỀ
# =========================================================================
st.title("🏸 Quản lý Sân Cầu Lông")

players = st.session_state.players

# =========================================================================
# PHẦN 1: THANH THỐNG KÊ NHANH (TOP DASHBOARD)
# =========================================================================
checked_in_list = [p for p in players if p["checked_in"]]
n_checked_in = len(checked_in_list)
n_vanglai_present = sum(1 for p in checked_in_list if p["guest_type"] == "Vãng lai")
n_ck = sum(1 for p in checked_in_list if p["payment"] == "CK")
n_tm = sum(1 for p in checked_in_list if p["payment"] == "TM")
n_unpaid = sum(1 for p in checked_in_list if p["payment"] == "Chưa thu")

c1, c2, c3 = st.columns(3)
c1.metric("✅ Đã đến", f"{n_checked_in}/{MAX_PLAYERS}")
c2.metric("🚶 Vãng lai có mặt", n_vanglai_present)
c3.metric("💰 Chưa thu", f"{n_unpaid} người")
st.caption(f"Đã thu: 💳 {n_ck} CK &nbsp;•&nbsp; 💵 {n_tm} TM", unsafe_allow_html=True)
st.divider()

# =========================================================================
# PHẦN 2: FORM THÊM KHÁCH MỚI (NHANH 1 DÒNG)
# =========================================================================
st.subheader("➕ Thêm khách mới")
if len(players) >= MAX_PLAYERS:
    st.warning(f"Đã đạt tối đa {MAX_PLAYERS} người, không thể thêm khách mới.")
else:
    with st.form("add_player_form", clear_on_submit=True):
        fc1, fc2 = st.columns([2, 1])
        name_in = fc1.text_input("Tên / Biệt danh", placeholder="VD: Minh")
        gender_in = fc2.selectbox("Giới tính", GENDER_OPTIONS)

        fc3, fc4 = st.columns(2)
        guest_in = fc3.selectbox("Loại khách", GUEST_OPTIONS)
        level_in = fc4.selectbox("Trình độ", LEVEL_OPTIONS)

        appearance_in = st.text_input("Đặc điểm nhận dạng", placeholder="VD: Áo đỏ, giày vàng")

        submitted = st.form_submit_button("➕ Thêm Khách", use_container_width=True)
        if submitted:
            if not name_in.strip():
                st.error("Vui lòng nhập tên khách.")
            else:
                add_player(name_in, gender_in, guest_in, level_in, appearance_in)
                st.success(f"Đã thêm {name_in}!")
                st.rerun()

st.divider()

# =========================================================================
# PHẦN 3: KHU VỰC ĐIỀU PHỐI 2 SÂN
# =========================================================================
st.subheader("🎯 Điều phối sân")


def render_level_badge(level):
    return level.split(" ")[0]  # chỉ lấy icon màu


def player_short_label(p):
    return (
        f"{render_level_badge(p['level'])}{p['gender'][0]} {p['name']} "
        f"({p['appearance']})" if p["appearance"] else
        f"{render_level_badge(p['level'])}{p['gender'][0]} {p['name']}"
    )


def render_court(court_num):
    court_key = f"court{court_num}"
    occupants = st.session_state[court_key]

    st.markdown(f"#### 🏟️ Sân {court_num}")

    if occupants:
        # --- Sân đang có người chơi ---
        for pid in occupants:
            p = get_player(pid)
            if p:
                st.markdown(
                    f"<div class='player-card'>{player_short_label(p)} "
                    f"&nbsp;<span class='small-note'>({p['matches']} trận)</span></div>",
                    unsafe_allow_html=True,
                )
        if st.button(f"🏁 Kết thúc trận Sân {court_num}", key=f"end_{court_num}", use_container_width=True):
            end_match(court_num)
            st.rerun()
        return

    # --- Sân đang trống: hiển thị 2 chế độ xếp sân ---
    st.caption("Sân đang trống.")
    tab_auto, tab_manual = st.tabs(["⚡ Tự động", "🖐️ Thủ công"])

    # ---- CHẾ ĐỘ TỰ ĐỘNG ----
    with tab_auto:
        sugg_key = f"suggestion{court_num}"
        colA, colB = st.columns(2)
        if colA.button(f"⚡ Gợi ý Sân {court_num}", key=f"suggest_{court_num}", use_container_width=True):
            result = suggest_court()
            if result is None:
                st.warning("Không đủ người đang chờ (cần tối thiểu 4 người đã check-in và chưa vào sân).")
                st.session_state[sugg_key] = None
            else:
                st.session_state[sugg_key] = result
            st.rerun()

        if st.session_state[sugg_key]:
            score, combo, pairing, repeat, balance = st.session_state[sugg_key]
            (p1, p2), (p3, p4) = pairing
            names = {pid: get_player(pid)["name"] for pid in combo}
            st.info(
                f"**Đội A:** {names[p1]} & {names[p2]}  \n"
                f"**Đội B:** {names[p3]} & {names[p4]}  \n"
                f"<span class='small-note'>Trùng lịch sử: {repeat} lần • Lệch trình độ: {balance}</span>",
                icon="🎾",
            )
            if colB.button(f"✅ Xác nhận Sân {court_num}", key=f"confirm_{court_num}", use_container_width=True):
                confirm_to_court(court_num, list(combo), pairing)
                st.session_state[sugg_key] = None
                st.rerun()

    # ---- CHẾ ĐỘ THỦ CÔNG ----
    with tab_manual:
        waiting = get_waiting_players()
        if len(waiting) < 4:
            st.caption("Cần tối thiểu 4 người đang chờ (đã check-in, chưa vào sân) để xếp thủ công.")
        else:
            waiting_sorted = sorted(waiting, key=lambda p: p["matches"])
            options = {f"{player_short_label(p)} — {p['matches']} trận": p["id"] for p in waiting_sorted}
            picked = st.multiselect(
                "Chọn đúng 4 người",
                options=list(options.keys()),
                key=f"manual_pick_{court_num}",
            )
            if st.button(f"➡️ Đưa vào Sân {court_num}", key=f"manual_confirm_{court_num}", use_container_width=True):
                if len(picked) != 4:
                    st.error("Vui lòng chọn đúng 4 người.")
                else:
                    ids = [options[label] for label in picked]
                    confirm_to_court(court_num, ids)  # chia đội mặc định 2-2 theo thứ tự chọn
                    st.rerun()


col_court1, col_court2 = st.columns(2)
with col_court1:
    render_court(1)
with col_court2:
    render_court(2)

st.divider()

# =========================================================================
# PHẦN 4: DANH SÁCH NGƯỜI CHƠI (SUPER COMPACT)
# =========================================================================
st.subheader(f"📋 Danh sách người chơi ({len(players)})")

if not players:
    st.caption("Chưa có người chơi nào. Hãy thêm khách ở Phần 2.")
else:
    # Sắp xếp: đã đến lên trước, rồi số trận ít nhất lên trước, rồi tên A-Z
    sorted_players = sorted(
        players,
        key=lambda p: (not p["checked_in"], p["matches"], p["name"].lower()),
    )

    for p in sorted_players:
        with st.container():
            row1 = st.columns([0.9, 3.6, 1.3])
            # --- Cột 1: check-in ---
            checked = row1[0].checkbox("", value=p["checked_in"], key=f"chk_{p['id']}")
            if checked != p["checked_in"]:
                p["checked_in"] = checked
                if not checked and p["on_court"]:
                    # nếu bỏ check-in mà đang trên sân -> gỡ khỏi sân luôn
                    ck = f"court{p['on_court']}"
                    if p["id"] in st.session_state[ck]:
                        st.session_state[ck].remove(p["id"])
                    p["on_court"] = None
                st.rerun()

            # --- Cột 2: thông tin gọn ---
            court_badge = f" 🏟️Sân{p['on_court']}" if p["on_court"] else ""
            guest_short = "🆕" if p["guest_type"] == "Vãng lai" else "👤"
            info = f"**{render_level_badge(p['level'])}{p['gender'][0]}{guest_short}** {p['name']}"
            if p["appearance"]:
                info += f" _({p['appearance']})_"
            info += court_badge
            row1[1].markdown(info)

            # --- Cột 3: số trận + nút +1 ---
            mc1, mc2 = row1[2].columns([1, 1])
            mc1.markdown(f"<div style='padding-top:6px;'>{p['matches']} trận</div>", unsafe_allow_html=True)
            if mc2.button("➕1", key=f"plus_{p['id']}"):
                p["matches"] += 1
                st.rerun()

            # --- Hàng 2: nút thanh toán ---
            row2 = st.columns([0.9, 1.4, 1.4, 1.4])
            row2[0].markdown("&nbsp;", unsafe_allow_html=True)
            ck_label = "✅💳 CK" if p["payment"] == "CK" else "💳 CK"
            tm_label = "✅💵 TM" if p["payment"] == "TM" else "💵 TM"
            if row2[1].button(ck_label, key=f"ck_{p['id']}"):
                p["payment"] = "Chưa thu" if p["payment"] == "CK" else "CK"
                st.rerun()
            if row2[2].button(tm_label, key=f"tm_{p['id']}"):
                p["payment"] = "Chưa thu" if p["payment"] == "TM" else "TM"
                st.rerun()
            pay_note = "⏳ Chưa thu" if p["payment"] == "Chưa thu" else "✔️ Đã thu"
            row2[3].markdown(f"<div style='padding-top:6px;font-size:0.75rem;'>{pay_note}</div>", unsafe_allow_html=True)

            st.markdown("<hr style='margin:2px 0;'>", unsafe_allow_html=True)

# =========================================================================
# GHI CHÚ CUỐI TRANG
# =========================================================================
st.caption(
    "💡 Dữ liệu được lưu tạm trong bộ nhớ phiên (session_state) — sẽ mất khi tải lại/đóng ứng dụng."
)