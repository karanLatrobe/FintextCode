# 📌 Fintext – Bank PDF Transaction Extractor & ML Transaction Type Predictor  
### 🚀 Django Web App | PDF Parsing | Machine Learning | User Authentication

---

## 🎥 Demo – How Fintext Works?

https://github.com/user-attachments/assets/da994dc3-1255-4671-b84e-0bcae583c597

---

## 📝 Overview

**Fintext** is an AI-driven system that:

- Extracts **bank transactions** from PDF statements  
- Cleans & structures the data into a usable format  
- Uses **Machine Learning** to classify the type of transactions  
- Provides a smooth **Django Web Interface** with:
  - 🔐 User Signup  
  - 🔑 User Login  
  - 👤 Profile Dashboard  
  - 📄 PDF Upload Page  
  - 📊 Extracted Transaction Table  
  - 🤖 ML-Predicted Labels  

The system automates banking data processing with end-to-end intelligence.

---

## ⚙️ Tech Stack

### **Backend**
- Python  
- Django  
- pdfplumber  
- Regular Expressions (Regex)  
- google/flan-t5-base

### **Frontend**
- Django Templates  
- HTML / CSS / JavaScript  

### **Database**
- SQLITE 3


## ✨ Features

### 🔎 Multi-Bank PDF Extraction  
Supports several banks including:
- SUNCORP
- Bendigo
- NAB
- ANZ Business Essentials  
- ANZ Plus  
- Westpac  
- Commonwealth  

Easily extendable via **common.py**.

---

### 🧠 ML-Based Transaction Type Prediction  
The model predicts categories like:

- Grocery  
- Utility  
- Food  
- Travel  
- Shopping  
- Entertainment  
- Subscription  
- And more…  

---

### 🌐 Authentication System  
- New user registration  
- Secure login  
- Personalized dashboard  
- User-specific PDF history  

---

### 📤 End-to-End Workflow  
1. User uploads the bank PDF  
2. Extractor processes and reads all transactions  
3. ML model predicts the transaction type  
4. Output displayed in an interactive table  
5. User can download/analyze results  

---

## ▶️ Installation Guide

### 1️⃣ Clone the Project
```bash
git clone https://github.com/karan89200/FIINTEXT.git
cd FIINTEXT

2️⃣ Create Virtual Environment
python -m venv venv
venv\Scripts\activate   # Windows

3️⃣ Install Requirements
pip install -r requirements.txt

4️⃣ Apply Migrations
python manage.py migrate

5️⃣ Start Django Server
python manage.py runserver




