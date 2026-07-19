import os
from flask import Flask

app = Flask(__name__)

NOTEBOOK_FILE = "ledger_notebook.txt" 

def load_notebook_memory():
    if not os.path.exists(NOTEBOOK_FILE):
        with open(NOTEBOOK_FILE, "w", encoding="utf-8") as f:
            f.write("")
        return []
    memory_data = []
    current_partition = {}
    with open(NOTEBOOK_FILE, "r", encoding="utf-8") as f:
        lines = f.readlines()
    for line in lines:
        line = line.strip()
        if "--- PARTITION ---" in line:
            if current_partition:
                memory_data.append(current_partition)
                current_partition = {}
        elif line.startswith("REFERENCE:"):
            current_partition["reference"] = line.replace("REFERENCE:", "").strip()
        elif line.startswith("KEY:"):
            current_partition["key"] = line.replace("KEY:", "").strip()
        elif line.startswith("PREDICTIONS:"):
            current_partition["predictions"] = line.replace("PREDICTIONS:", "").strip()
        elif line.startswith("ACTUAL_RESULTS:"):
            current_partition["actual_results"] = line.replace("ACTUAL_RESULTS:", "").strip()
    if current_partition:
        memory_data.append(current_partition)
    return memory_data 

def auto_fix_missing_spaces(input_str):
    tokens = input_str.split()
    fixed_tokens = []
    for token in tokens:
        if len(token) == 6:
            fixed_tokens.append(token[:3])
            fixed_tokens.append(token[3:])
        else:
            fixed_tokens.append(token)
    return " ".join(fixed_tokens) 

def extract_horizontal_transitions(columns_list):
    transitions = []
    for i in range(1, len(columns_list)):
        prev_col = columns_list[i-1]
        curr_col = columns_list[i]
        col_trans = []
        for r in range(3):
            if r < len(prev_col) and r < len(curr_col):
                col_trans.append(0 if prev_col[r] == curr_col[r] else 1)
            else:
                col_trans.append(0)
        transitions.append(col_trans)
    return transitions 

def calculate_total_key_shift_ratio(key_list):
    total_rounds = 0
    total_shifts = 0
    for i in range(1, len(key_list)):
        prev_col = key_list[i-1]
        curr_col = key_list[i]
        for r in range(3):
            if r < len(prev_col) and r < len(curr_col):
                total_rounds += 1
                if prev_col[r] != curr_col[r]:
                    total_shifts += 1
    return int((total_shifts / max(1, total_rounds)) * 100) 

def generate_predictions_mirror_shifts(ref_list, key_list, memory_data):
    predictions = []
    opponents = {"B": "P", "P": "B"}
    live_full_track = ref_list + key_list
    live_shift_pct = calculate_total_key_shift_ratio(live_full_track)
    live_b_count = sum(col.count("B") for col in key_list[:8])
    live_p_count = sum(col.count("P") for col in key_list[:8])
    dominant_live_char = "B" if live_b_count >= live_p_count else "P"
    final_resolved_transitions = []
    for i in range(10):
        col_decision = []
        for r in range(3):
            vote_static = 0
            vote_shift = 0
            match_found = False
            for partition in memory_data:
                p_ref = partition.get("reference", "").split()
                p_key = partition.get("key", "").split()
                p_actuals = partition.get("actual_results", "").split()
                if len(p_key) >= 8 and len(p_actuals) >= 10:
                    hist_full_track = p_ref + p_key
                    hist_pct = calculate_total_key_shift_ratio(hist_full_track)
                    if abs(hist_pct - live_shift_pct) <= 15:
                        full_hist = hist_full_track + p_actuals
                        hist_trans = extract_horizontal_transitions(full_hist)
                        hist_idx = (len(hist_full_track) - 1) + i
                        if hist_idx < len(hist_trans):
                            match_found = True
                            if hist_trans[hist_idx][r] == 0: vote_static += 1
                            else: vote_shift += 1
            if match_found and (vote_shift + vote_static > 0):
                col_decision.append("SHIFT" if vote_shift >= vote_static else "STATIC")
            else:
                round_counter = (i * 3) + r + 1
                col_decision.append("SHIFT" if (round_counter * 31) % 100 <= live_shift_pct else "STATIC")
        final_resolved_transitions.append(col_decision)
    last_column = key_list[-1]
    for i in range(10):
        preds_col = []
        decision = final_resolved_transitions[i]
        for r in range(3):
            prev_char = last_column[r] if r < len(last_column) else dominant_live_char
            if decision[r] == "SHIFT": preds_col.append(opponents.get(prev_char, dominant_live_char))
            else: preds_col.append(prev_char)
        if i == 0: preds_col[0] = opponents.get(preds_col[0], dominant_live_char)
        if i >= 2:
            prev_1 = predictions[i-1]
            prev_2 = predictions[i-2]
            if (prev_1[0] == prev_1[1] == prev_1[2]) and (prev_2[0] == prev_2[1] == prev_2[2]):
                preds_col[0] = opponents.get(preds_col[0], dominant_live_char)
                preds_col[2] = opponents.get(preds_col[2], dominant_live_char)
            elif prev_1 == prev_2: preds_col[1] = opponents.get(preds_col[1], dominant_live_char)
        final_col_str = "".join(preds_col)
        predictions.append(final_col_str)
        last_column = final_col_str
    return " ".join(predictions), live_shift_pct 

# --- Web Interface (Flask) ---
@app.route('/')
def home():
    return "Baccarat Engine is running and Active!"

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
