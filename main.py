from flask import Flask, request, jsonify, send_from_directory  ,render_template
from flask_cors import CORS
import os
import json
from datetime import datetime
import requests
app = Flask(__name__)
CORS(app)


@app.route('/')
def portfol():
    return render_template("Present.html")

@app.route('/News')
def RenderNews():
    return render_template("index.html")



@app.route('/process_ui')
def process_ui():
    return render_template("process_ui.html")

# 🟢 حفظ المقالات حسب النوع
@app.route('/save_articles', methods=['POST'])
def save_articles():
    data = request.get_json()
    article_type = data.get("type")
    new_articles = data.get("articles")

    if not article_type or not isinstance(new_articles, list):
        return jsonify({"status": "error", "message": "Invalid data"}), 400

    folder_name = f"{article_type.lower()}_Articles"
    os.makedirs(folder_name, exist_ok=True)

    file_path = os.path.join(folder_name, f"{article_type.lower()}_raw.json")

    existing_articles = []
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            try:
                existing_articles = json.load(f)
            except:
                existing_articles = []

    existing_keys = {f"{a.get('title')}|{a.get('link')}" for a in existing_articles}
    unique_articles = []
    for article in new_articles:
        key = f"{article.get('title')}|{article.get('link')}"
        if key not in existing_keys:
            unique_articles.append(article)
            existing_keys.add(key)

    combined_articles = existing_articles + unique_articles

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(combined_articles, f, ensure_ascii=False, indent=2)

    print(f"✅ Received: {len(new_articles)} articles.")
    print(f"➕ New unique: {len(unique_articles)}")
    print(f"💾 Total saved: {len(combined_articles)}")

    return jsonify({
        "status": "saved",
        "type": article_type,
        "new": len(unique_articles),
        "total": len(combined_articles)
    })

@app.route('/process_articles', methods=['GET'])
def process_articles():
    categories = [
        "World", "Local", "Business", "Technology",
        "Entertainment", "Sports", "Science", "Health"
    ]

    output_logs = ""  # 👈 لتجميع السطور في المتصفح

    for category in categories:
        folder_name = f"{category.lower()}_Articles"
        raw_file = os.path.join(folder_name, f"{category.lower()}_raw.json")
        output_file = os.path.join(folder_name, f"{category.lower()}.json")
        image_dir = os.path.join(folder_name, "images")

        if not os.path.exists(raw_file):
            output_logs += f"❌ Skipping {category} — file not found: {raw_file}\n"
            continue

        os.makedirs(image_dir, exist_ok=True)

        try:
            with open(raw_file, "r", encoding="utf-8") as f:
                articles = json.load(f)
        except Exception as e:
            output_logs += f"❌ Error reading {raw_file}: {e}\n"
            continue

        processed = []
        output_logs += f"\n🔄 Processing {category} ({len(articles)} articles)\n"

        for article in articles:
            published = article.get("published")
            if published:
                try:
                    dt = datetime.fromisoformat(published.replace("Z", ""))
                    article["publishid"] = f"{dt.year}-{dt.month}-{dt.day}"
                    article["time"] = dt.strftime("%H:%M%S")
                except:
                    article["publishid"] = None
                    article["time"] = None

            image_url = article.get("image")
            if image_url and image_url.startswith("/api/attachments/"):
                full_url = "https://news.google.com" + image_url
                article["image"] = full_url

                filename_base = image_url.split("/")[-1].split("=")[0].split("?")[0]
                filename = filename_base + ".png"
                image_path = os.path.join(image_dir, filename)

                if not os.path.exists(image_path):
                    try:
                        img_data = requests.get(full_url, timeout=10).content
                        with open(image_path, "wb") as f:
                            f.write(img_data)
                        article["imageInternal"] = filename
                        output_logs += f"📥 Downloaded: {filename}\n"
                    except Exception as e:
                        article["imageInternal"] = None
                        output_logs += f"⚠️ Image failed ({category}): {full_url}\n{e}\n"
                else:
                    article["imageInternal"] = filename
                    output_logs += f"✅ Already exists: {filename}\n"

            processed.append(article)

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(processed, f, ensure_ascii=False, indent=2)

        output_logs += f"✅ Done: {category} → {len(processed)} articles saved to {output_file}\n"
        os.remove(raw_file)

    return f"<pre>{output_logs}</pre>"

# 🟢 جلب جميع المقالات من جميع المجلدات *_Articles
@app.route('/api/articale', methods=['GET'])
def get_all_articles():
    base_dir = os.getcwd()
    global_articles = []
    id_counter = 1

    for folder in os.listdir(base_dir):
        if folder.endswith('_Articles') and os.path.isdir(os.path.join(base_dir, folder)):
            category = folder.replace('_Articles', '')
            folder_path = os.path.join(base_dir, folder)

            for filename in os.listdir(folder_path):
                if filename.endswith('.json'):
                    file_path = os.path.join(folder_path, filename)

                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            articles = json.load(f)
                            if isinstance(articles, dict):  # ملف واحد
                                articles = [articles]
                    except:
                        continue

                    for article in articles:
                        image_internal = article.get('imageInternal', '')
                        global_articles.append({
                            'id': id_counter,
                            'title': article.get('title', ''),
                            'description': article.get('description', ''),
                            'imageUrl': f"./{folder}/images/{image_internal}" if image_internal else '',
                            'source': article.get('author', 'Unknown'),
                            'urlArtical':article.get('link', 'Unknown'),
                            'time': article.get('time', ''),
                            'publishid': article.get('publishid', ''),
                            'category': category
                        })
                        id_counter += 1

    return jsonify(global_articles)


# 🟢 عرض الصور من أي مجلد مقالات
@app.route('/<folder>/images/<filename>')
def serve_image(folder, filename):
    directory = os.path.join(os.getcwd(), folder, 'images')
    return send_from_directory(directory, filename)


if __name__ == '__main__':
    app.run(debug=True)
