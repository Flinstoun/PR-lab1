from flask import Flask, jsonify, request
import json
import os

app = Flask(__name__)

# Инициализация данных
PRODUCTS_FILE = 'products.json'

# Проверяем существование файла с продуктами
if not os.path.exists(PRODUCTS_FILE):
    with open(PRODUCTS_FILE, 'w') as f:
        json.dump([
            {"id": 1, "name": "Laptop", "price": 999.99, "available": True},
            {"id": 2, "name": "Smartphone", "price": 499.99, "available": True},
            {"id": 3, "name": "Headphones", "price": 99.99, "available": True}
        ], f)

def get_products():
    with open(PRODUCTS_FILE, 'r') as f:
        return json.load(f)

def save_products(products):
    with open(PRODUCTS_FILE, 'w') as f:
        json.dump(products, f)

# GET: получение всех продуктов
@app.route('/api/products', methods=['GET'])
def get_all_products():
    return jsonify(get_products())

# GET: получение конкретного продукта по ID
@app.route('/api/products/<int:product_id>', methods=['GET'])
def get_product(product_id):
    products = get_products()
    product = next((p for p in products if p['id'] == product_id), None)
    
    if product:
        return jsonify(product)
    return jsonify({"error": "Product not found"}), 404

# POST: создание нового продукта
@app.route('/api/products', methods=['POST'])
def create_product():
    if not request.json or 'name' not in request.json:
        return jsonify({"error": "Invalid product data"}), 400
    
    products = get_products()
    
    # Генерация нового ID
    new_id = max(p['id'] for p in products) + 1 if products else 1
    
    new_product = {
        'id': new_id,
        'name': request.json['name'],
        'price': request.json.get('price', 0),
        'available': request.json.get('available', True)
    }
    
    products.append(new_product)
    save_products(products)
    
    return jsonify(new_product), 201

# PUT: обновление существующего продукта
@app.route('/api/products/<int:product_id>', methods=['PUT'])
def update_product(product_id):
    if not request.json:
        return jsonify({"error": "Invalid product data"}), 400
    
    products = get_products()
    product = next((p for p in products if p['id'] == product_id), None)
    
    if not product:
        return jsonify({"error": "Product not found"}), 404
    
    product['name'] = request.json.get('name', product['name'])
    product['price'] = request.json.get('price', product['price'])
    product['available'] = request.json.get('available', product['available'])
    
    save_products(products)
    
    return jsonify(product)

# DELETE: удаление продукта
@app.route('/api/products/<int:product_id>', methods=['DELETE'])
def delete_product(product_id):
    products = get_products()
    product = next((p for p in products if p['id'] == product_id), None)
    
    if not product:
        return jsonify({"error": "Product not found"}), 404
    
    products = [p for p in products if p['id'] != product_id]
    save_products(products)
    
    return jsonify({"message": f"Product {product_id} deleted successfully"})

# Проверка доступности сервиса
@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy", "service": "product-service"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)