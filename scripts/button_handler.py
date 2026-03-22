# scripts/button_handler.py (дополняем)
from flask import Flask, request, jsonify
import os
import json
import sys

# Добавляем путь к модулям
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

from scripts.run_products_report import create_products_sheet
from scripts.run_prices_report import load_prices

app = Flask(__name__)

# Загружаем credentials
GOOGLE_CREDENTIALS = json.loads(os.getenv('GOOGLE_CREDENTIALS_JSON', '{}'))

@app.route('/')
def index():
    return """
    <h1>Ozon Reports API</h1>
    <p>Доступные эндпоинты:</p>
    <ul>
        <li>POST /run-products - Загрузить товары</li>
        <li>POST /run-prices - Загрузить цены</li>
        <li>GET /health - Проверка здоровья</li>
    </ul>
    """

@app.route('/run-products', methods=['POST'])
def run_products():
    """Эндпоинт для запуска загрузки товаров"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'success': False, 'error': 'No JSON data provided'}), 400
        
        spreadsheet_id = data.get('spreadsheet_id')
        
        if not spreadsheet_id:
            return jsonify({'success': False, 'error': 'spreadsheet_id is required'}), 400
        
        # Запускаем создание листа
        success = create_products_sheet(spreadsheet_id, GOOGLE_CREDENTIALS)
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Products sheet created successfully'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to create products sheet'
            }), 500
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/run-prices', methods=['POST'])
def run_prices_endpoint():
    """Эндпоинт для запуска загрузки цен"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'success': False, 'error': 'No JSON data provided'}), 400
        
        spreadsheet_id = data.get('spreadsheet_id')
        overwrite = data.get('overwrite', False)
        
        if not spreadsheet_id:
            return jsonify({'success': False, 'error': 'spreadsheet_id is required'}), 400
        
        # Запускаем загрузку цен
        success = load_prices(spreadsheet_id, GOOGLE_CREDENTIALS, overwrite)
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Prices loaded successfully'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to load prices'
            }), 500
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({'status': 'ok'})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8080)