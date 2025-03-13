from flask import Flask, jsonify, request
import json
import os
import requests

app = Flask(__name__)

# Инициализация данных
ORDERS_FILE = 'orders.json'
PRODUCT_SERVICE_URL = os.environ.get('PRODUCT_SERVICE_URL', 'http://product:5000')

# Проверяем существование файла с заказами
if not os.path.exists(ORDERS_FILE):
    with open(ORDERS_FILE, 'w') as f:
        json.dump([], f)

def get_orders():
    with open(ORDERS_FILE, 'r') as f:
        return json.load(f)

def save_orders(orders):
    with open(ORDERS_FILE, 'w') as f:
        json.dump(orders, f)

# GET: получение всех заказов
@app.route('/api/orders', methods=['GET'])
def get_all_orders():
    return jsonify(get_orders())

# GET: получение конкретного заказа по ID
@app.route('/api/orders/<int:order_id>', methods=['GET'])
def get_order(order_id):
    orders = get_orders()
    order = next((o for o in orders if o['id'] == order_id), None)
    
    if order:
        # Получаем информацию о продуктах из product-service
        for item in order['items']:
            try:
                response = requests.get(f"{PRODUCT_SERVICE_URL}/api/products/{item['product_id']}")
                if response.status_code == 200:
                    item['product_details'] = response.json()
            except requests.RequestException as e:
                app.logger.error(f"Error fetching product details: {e}")
        
        return jsonify(order)
    return jsonify({"error": "Order not found"}), 404

# POST: создание нового заказа
@app.route('/api/orders', methods=['POST'])
def create_order():
    if not request.json or 'items' not in request.json:
        return jsonify({"error": "Invalid order data"}), 400
    
    # Проверяем доступность продуктов
    for item in request.json['items']:
        if 'product_id' not in item:
            return jsonify({"error": "Product ID is required for each item"}), 400
        
        try:
            response = requests.get(f"{PRODUCT_SERVICE_URL}/api/products/{item['product_id']}")
            if response.status_code != 200:
                return jsonify({"error": f"Product with ID {item['product_id']} not found"}), 404
            
            product = response.json()
            if not product.get('available', False):
                return jsonify({"error": f"Product {product['name']} is not available"}), 400
                
        except requests.RequestException as e:
            app.logger.error(f"Error checking product availability: {e}")
            return jsonify({"error": "Could not connect to product service"}), 503
    
    orders = get_orders()
    
    # Генерация нового ID
    new_id = max(o['id'] for o in orders) + 1 if orders else 1
    
    new_order = {
        'id': new_id,
        'customer_name': request.json.get('customer_name', 'Guest'),
        'items': request.json['items'],
        'status': 'pending'
    }
    
    orders.append(new_order)
    save_orders(orders)
    
    return jsonify(new_order), 201

# PUT: обновление существующего заказа
@app.route('/api/orders/<int:order_id>', methods=['PUT'])
def update_order(order_id):
    if not request.json:
        return jsonify({"error": "Invalid order data"}), 400
    
    orders = get_orders()
    order = next((o for o in orders if o['id'] == order_id), None)
    
    if not order:
        return jsonify({"error": "Order not found"}), 404
    
    order['customer_name'] = request.json.get('customer_name', order['customer_name'])
    
    if 'items' in request.json:
        # Проверяем доступность продуктов при изменении заказа
        for item in request.json['items']:
            if 'product_id' not in item:
                return jsonify({"error": "Product ID is required for each item"}), 400
            
            try:
                response = requests.get(f"{PRODUCT_SERVICE_URL}/api/products/{item['product_id']}")
                if response.status_code != 200:
                    return jsonify({"error": f"Product with ID {item['product_id']} not found"}), 404
            except requests.RequestException as e:
                app.logger.error(f"Error checking product availability: {e}")
                return jsonify({"error": "Could not connect to product service"}), 503
        
        order['items'] = request.json['items']
    
    order['status'] = request.json.get('status', order['status'])
    
    save_orders(orders)
    
    return jsonify(order)

# DELETE: удаление заказа
@app.route('/api/orders/<int:order_id>', methods=['DELETE'])
def delete_order(order_id):
    orders = get_orders()
    order = next((o for o in orders if o['id'] == order_id), None)
    
    if not order:
        return jsonify({"error": "Order not found"}), 404
    
    orders = [o for o in orders if o['id'] != order_id]
    save_orders(orders)
    
    return jsonify({"message": f"Order {order_id} deleted successfully"})

# Проверка доступности сервиса
@app.route('/health', methods=['GET'])
def health_check():
    # Проверяем также доступность product-service
    product_service_status = "unavailable"
    try:
        response = requests.get(f"{PRODUCT_SERVICE_URL}/health")
        if response.status_code == 200:
            product_service_status = "available"
    except requests.RequestException:
        pass
    
    return jsonify({
        "status": "healthy",
        "service": "order-service",
        "dependencies": {
            "product-service": product_service_status
        }
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)