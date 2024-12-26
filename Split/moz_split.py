import spacy
import re
import os
import tempfile
from datetime import datetime
import csv

# SpaCyの大規模モデルをロード
try:
    nlp = spacy.load("en_core_web_trf")
except Exception as e:
    print(f"Error loading SpaCy model: {e}")
    nlp = None

# 固有名詞として誤認識されやすい単語をリストに追加
proper_nouns = {"monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday",
                "january", "february", "march", "april", "may", "june", "july", "august",
                "september", "october", "november", "december"}
prefixes = ["pre", "part", "intra", "inter", "sub", "life","self", "trans", "hyper", "hypo", "post", "anti", "auto", "bi", "co", "de", "dis", "en", "extra", "micro", "mid", "mono", "non", "over", "peri", "pro", "re", "semi", "super", "ultra", "un", "under"]

def process_text(text):
    
    # 文を解析
    try:
        doc = nlp(text)
        result = []
        capitalize_next = True
        
        for token in doc:
            # 文頭を大文字化
            if capitalize_next:
                result.append(token.text.capitalize())
                capitalize_next = False
            # I'mの処理
            elif token.text.lower() == "i'm":
                result.append("I'm")
            # Iの処理
            elif token.text.lower() == "i":
                result.append("I")
            # Mayの処理
            elif token.text.lower() == "may":
                if token.ent_type_ == "DATE":  # 日付としてのMay
                    result.append("May")
                elif token.dep_ == "aux" or token.dep_ == "ROOT":  # 助動詞としてのmay
                    result.append("may")
                else:
                    result.append(token.text.capitalize())
            # 固有名詞の大文字化
            elif token.text.lower() in proper_nouns or token.ent_type_ in ["PERSON", "ORG", "GPE", "LOC"]:
                result.append(token.text.capitalize())
            else:
                result.append(token.text)
            
            # 文の終わりで次の単語を大文字にするフラグを立てる
            if token.text in [".", "!", "?"]:
                capitalize_next = True

        # 結果を修正（アポストロフィーやピリオド、カンマの前のスペースを取り除く）
        processed_text = " ".join(result)
        processed_text = re.sub(r'\s+([.,!?\'"])', r'\1', processed_text)  # 記号の前のスペースを削除
        processed_text = re.sub(r"'\s+", "'", processed_text)  # アポストロフィー後のスペースを削除

        # 否定形や縮約形の修正
        contraction_patterns = [
            
            (r'\s+-\s*free', '-free'),
            (r"\b([Dd])o\s+n't\b", r"\1on't"),
            (r"\b([Cc])a\s+n['‘’]t\b", r"\1an't"),
            (r"\b([Ww])o\s+n't\b", r"\1on't"),
            (r"\b([Ss])ha\s+n't\b", r"\1han't"),
            (r"\b([Ii])s\s+n't\b", r"\1sn't"),
            (r"\b([Ww])as\s+n't\b", r"\1asn't"),#自作
            (r"\b([Aa])re\s+n't\b", r"\1ren't"),
            (r"\b([Ww])ere\s+n't\b", r"\1eren't"),#自作
            (r"\b([Yy])ou\s+'re\b", r"\1ou're"),
            (r"\b([Ww])e\s+'re\b", r"\1e're"),
            (r"\b([Tt])hey\s+'re\b", r"\1hey're"),
            (r"\b([Ii])'m\b", r"\1'm"),
            (r"\b([Dd])id\s+n't\b", r"\1idn't"),
            (r"\b([Dd])oes\s+n't\b", r"\1oesn't"),
            (r"\b([Hh])as\s+n't\b", r"\1asn't"),
            (r"\b([Hh])ave\s+n't\b", r"\1aven't"),
            (r"\b([Ww])ould\s+n't\b", r"\1ouldn't"),
            (r"\b([Cc])ould\s+n't\b", r"\1ouldn't"),
            (r"\b([Ss])hould\s+n't\b", r"\1houldn't"),
            (r"\b([Mm])ight\s+n't\b", r"\1ightn't"),
            (r"\b([Mm])ust\s+n't\b", r"\1ustn't"),
            (r"\b([Ii])'ve\b", r"\1've"),
            (r"\b([Yy])ou\s+'ve\b", r"\1ou've"),
            (r"\b([Ww])e\s+'ve\b", r"\1e've"),
            (r"\b([Tt])hey\s+'ve\b", r"\1hey've")
        ]

        for pattern, repl in contraction_patterns:
            processed_text = re.sub(pattern, repl, processed_text)
        for prefix in prefixes:
            processed_text=processed_text.replace(f" {prefix} - ",f" {prefix}-").replace(f" {prefix} -",f" {prefix}-").replace(f" {prefix}- ",f" {prefix}-")
        

        return processed_text
    except Exception as e:
        print(f"Error processing text: {text[:50]} - {e}")
        return text  # エラー時は元のテキストを返す

def process_srt_file(queue,file_path,output_name):
    
    try:
        with open("replacements.csv", newline='', encoding='utf-8') as csvfile:
            reader = csv.reader(csvfile)
            next(reader)  # ヘッダーをスキップ
            replacements = [(row[0], row[1]) for row in reader]

        with open(file_path, "r", encoding="utf-8") as file:
            lines = file.readlines()

        total_steps = len(lines)  # 全行数をtotal_stepsに設定
        #progress_bar = st.progress(0)  # Streamlitの進捗バーを初期化

        processed_lines = []
        
        for i, line in enumerate(lines):
            # SRTファイルのタイムコード部分はそのまま維持
            if re.match(r'\d{2}:\d{2}:\d{2},\d{3} --> \d{2}:\d{2}:\d{2},\d{3}', line):
                processed_lines.append(line)
            # 番号部分もそのまま維持
            elif re.match(r'\d+', line):
                processed_lines.append(line)
                
            # それ以外はテキストとして処理
            else:
                try:
                    processed_text = process_text(line.strip())
                
                    for original, replacement in replacements:
                        original=re.escape(original)
                        new_original = rf"\b{original}\b"
                        processed_text = re.sub(new_original, replacement, processed_text)
                    processed_lines.append(processed_text + "\n")
                    if i%5==0:
                        queue.put(("progress",(0.8+0.2*(i+1)/total_steps)))
                    
                except Exception as e:
                    # エラーをログに記録
                    print(f"Error processing line {i}: {line.strip()} - {e}")
                    # エラーが発生した行をそのまま追加（必要に応じて変更）
                    processed_lines.append(line)


        # 結果を新しいSRTファイルに保存
        
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        temp_dir = os.path.join(tempfile.gettempdir(), f"tempdir_{timestamp}")
        os.makedirs(temp_dir, exist_ok=True)

        output_file = os.path.join(temp_dir,output_name)
        with open(output_file, "w", encoding="utf-8") as file:
            file.writelines(processed_lines)

        return output_file
    except Exception as e:
        print(f"Error processing SRT file {file_path}: {e}")
        return None
def process_text_file(input_file, output_name,replace_word=True):
    try:
        if replace_word==True:
        
            with open("replacements.csv", newline='', encoding='utf-8') as csvfile:
                reader = csv.reader(csvfile)
                next(reader)  # ヘッダーをスキップ
                replacements = [(row[0], row[1]) for row in reader]

        # 入力ファイルを読み込んで、テキストを処理
        with open(input_file, "r", encoding="utf-8") as file:
            text = file.read()

        # テキストを処理
        processed_text = process_text(text)
        if replace_word==True:
            for original, replacement in replacements:
                original=re.escape(original)
                new_original = rf"\b{original}\b"
                processed_text = re.sub(new_original, replacement, processed_text)    
        # 結果を新しいSRTファイルに保存

        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        temp_dir = os.path.join(tempfile.gettempdir(), f"tempdir_{timestamp}")
        os.makedirs(temp_dir, exist_ok=True)

        output_file = os.path.join(temp_dir,output_name)
        output_file_R=output_file.replace("NR","R")
        
        R_text=processed_text
        with open("dot_manager.csv", newline='',encoding='utf-8') as dot_csvfile:
            reader = csv.reader(dot_csvfile)
            next(reader)
            dot_replacements = [(row[0],row[1]) for row in reader]
        
        for dot_original, dot_replacement in dot_replacements:
            r_dot_original=re.escape(dot_original)
            dot_new_original = rf"\b{r_dot_original}"
            R_text = re.sub(dot_new_original, dot_replacement, R_text)  
        
        R_text=R_text.replace(". ",".\n").replace("? ","?\n").replace("[dot]",".")


        # 結果を出力ファイルに保存
        with open(output_file, "w", encoding="utf-8") as file:
            file.write(processed_text)

        with open(output_file_R,"w",encoding="utf-8") as f:
            f.write(R_text)
        return output_file,output_file_R

    except Exception as e:
        print(f"Error processing SRT file {input_file}: {e}")
        return None,None

