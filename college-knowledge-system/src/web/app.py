import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from flask import Flask, request, jsonify, send_from_directory
from src.reasoning import engine
from src.graph.build_graph import load_graph

DATA_DIR = PROJECT_ROOT / 'data'
STATIC_DIR = Path(__file__).resolve().parent / 'static'

app = Flask(__name__, static_folder=str(STATIC_DIR))

@app.route('/')
def index():
    return send_from_directory(str(STATIC_DIR), 'index.html')

@app.route('/query', methods=['POST'])
def query():
    try:
        data = request.get_json()
        if not data or 'text' not in data:
            return jsonify({"error": "No text provided"}), 400
            
        text = data['text']
        
        # Call engine
        result = engine.answer('situation', text=text, use_cache=False)
        
        # Load graph
        graph_path = DATA_DIR / 'graph' / 'knowledge_graph.json'
        graph = load_graph(graph_path)
        
        # Render paragraph
        rendered_paragraph = engine.render_with_excerpts(result, graph)
        
        # Reshape ranked_colleges if present
        if 'ranked_colleges' in result:
            result['colleges_considered'] = [c.get('college', 'Unknown') for c in result.get('ranked_colleges', [])]
            new_summary = {}
            for c in result.get('ranked_colleges', []):
                college = c.get('college', 'Unknown')
                for topic, s_data in c.get('sentiment_summary', {}).items():
                    new_summary[f"{college} - {topic}"] = s_data
            result['sentiment_summary'] = new_summary
            
        response_data = {
            "colleges_considered": result.get('colleges_considered', []),
            "sentiment_summary": result.get('sentiment_summary', {}),
            "rendered_paragraph": rendered_paragraph,
            "supporting_comment_count": result.get('supporting_comment_count', 0),
            "confidence_note": result.get('confidence_note', ''),
            "agreement_level": result.get('agreement_level', '')
        }
        
        # Include roi_analysis if present
        if 'roi_analysis' in result:
            response_data['roi_analysis'] = result['roi_analysis']
            
        return jsonify(response_data)
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)
