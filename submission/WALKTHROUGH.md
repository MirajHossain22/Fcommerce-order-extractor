# Walkthrough Video Script & Demo Checklist

**Project:** F-Commerce Order Extractor ("Order Desk")  
**Target Duration:** 3:45 to 4:15 (Target ~600 words spoken naturally at ~140 wpm)  
**Candidate:** Miraj Hossain  
**Role:** Frontend Engineer Intern at Credosis  

---

## 📋 Pre-Recording Checklist & Demo Setup

Before hitting record, prepare your workspace with these exact tabs and windows:

### 1. Browser Windows Setup
- **Window 1 (Desktop View - 100% Zoom):**
  - Open `https://fcommerce-order-extractor.onrender.com/`
  - Have it at the login screen showing the **"⚡ Fill Demo Key"** button.
- **Window 2 (Mobile View / DevTools Device Toolbar):**
  - Open Chrome DevTools (`F12` or `Ctrl+Shift+I`).
  - Toggle Device Toolbar (`Ctrl+Shift+M`) set to **iPhone 14** or **Samsung Galaxy S20** (approx 390px to 412px width).
  - This tab will receive the checkout link `/buy/<token>`.
- **Window 3 (Editor / Code View - Optional background):**
  - VS Code open with `frontend/buyer.js` or `frontend/seller.js` ready if you want a 10-second code glimpse.

### 2. Prepared Test Data (Keep in a notepad to paste):
- **Demo Seller Key:** `demo-seller-key`
- **Sample Bangla/Banglish Chat Text (for AI Extraction):**
  ```text
  Bhai 1 ta Navy Blue Panjabi (L size) lagbe. 
  Address: House 12, Road 4, Sector 10, Uttara, Dhaka. 
  Phone: 01712345678. Urgent delivery please!
  ```
- **Sample Buyer Details (for Checkout form):**
  - Name: `Arif Hasan`
  - Phone: `01712345678`
  - Address: `House 14, Road 3, Sector 9, Uttara, Dhaka`

---

## 🎙️ Spoken Video Script (Word count: ~615 words)

### [0:00 - 0:15] Introduction (15s)
*"Hello everyone! I’m Miraj Hossain, and this is my Phase 02 demonstration of the **F-Commerce Order Extractor**, which I call **Order Desk**.*  
*I built this project for the Frontend Engineer Intern position at Credosis to solve a daily frustration faced by thousands of online sellers in Bangladesh."*

---

### [0:15 - 0:55] The Problem (40s)
*"In Bangladesh, most online shopping happens through Facebook and Messenger chats. While chatting is convenient for customers, it creates a massive operational nightmare for sellers.*  
*Customer addresses get lost in long message threads. Sellers struggle to track live inventory, leading to overselling items that are already out of stock.*  
*And customers have to repeatedly ping the seller asking, 'Bhai, where is my parcel?' because there is no transparent tracking. Both sides cope by taking screenshots, searching old chat logs, and dealing with delivery delays."*

---

### [0:55 - 1:25] The Solution (30s)
*"Order Desk bridges this gap with a lightweight, zero-install architecture.*  
*Instead of forcing customers to download an app or register an account, the seller uses this dashboard to turn messy chats into verified drafts, and generates a **mobile-first private checkout link**.*  
*The customer opens the link right inside Messenger, confirms their delivery details in 30 seconds, and gets an instant receipt and tracking link."*

---

### [1:25 - 2:25] Core Feature Demo: Checkout Link & Buyer Flow (60s)
*[Action: Click '⚡ Fill Demo Key' on login screen, then click 'Open order desk'. Dashboard appears immediately.]*  
*"Let’s see the core feature in action. I’ll sign into the Order Desk using the demo key.*  

*[Action: Click on order draft 'Arif Hasan'. Point to line items and total.]*  
*Here we have an order draft for Arif Hasan. Notice the items, size, and total BDT price.*  

*[Action: Click 'Create checkout link'. Show generated URL in the share box. Click 'Copy'.]*  
*Now, the seller clicks 'Create checkout link'. The system creates a secure, cryptographically hashed token that expires in 24 hours. The seller pastes this link directly into the customer's Messenger chat.*  

*[Action: Switch to the mobile-width browser tab and paste the link.]*  
*This is what the customer sees on their phone inside Messenger. It’s completely responsive and bilingual.*  
*The buyer reviews their items, delivery charge, and the Cash on Delivery total.*  

*[Action: Type customer name 'Arif Hasan', phone '01712345678', address 'House 14, Road 3, Sector 9, Uttara', then click 'Confirm order'.]*  
*The buyer enters their name, validated Bangladeshi mobile number, and address, and taps 'Confirm Order'.*  

*[Action: Confirmation screen appears with a green checkmark. Click 'Follow order updates'.]*  
*Instantly, the order is locked, catalog stock is deducted, and the buyer receives a permanent, private tracking link with a complete order timeline."*

---

### [2:25 - 3:55] Supporting Features Demo (90s)
*[Action: Switch back to the seller dashboard desktop view. Click 'Refresh list'.]*  
*"Back on the seller workspace, let’s look at our supporting features.*  

*[Action: Point to top metric bar: Total orders, Need review, In progress, Delivered.]*  
*First, the **Order Desk Dashboard**. Notice Arif's order moved from 'Draft' to 'Confirmed'. We have live metric cards and instant search filtering by customer name or product.*  

*[Action: Select Arif's confirmed order. In the status dropdown, select 'Packed' then 'Update status'. Then select 'Shipped'.]*  
*Second, the **Fulfillment State Machine**. Orders follow a strict lifecycle so status never gets mixed up. Once packed and shipped, I can attach courier details.*  

*[Action: Type courier name 'Steadfast Courier' and reference 'ST-982341'. Click 'Save courier info'.]*  
*I’ll enter Steadfast Courier and consignment tracking reference ST-982341. When I save this, the buyer's private tracking page updates automatically in real time.*  

*[Action: Click on 'Products & inventory stock' accordion to expand catalog.]*  
*Third, **Real-Time Stock Tracking**. Notice our catalog has size and color variants with low-stock alerts. When Arif confirmed his Panjabi earlier, the inventory was automatically decremented in the exact same database transaction. If an item is returned, we can inspect it and restock it with a single click, completely protected against double-restocking.*  

*[Action: Click '+ New order draft' at the top. Paste sample chat message into the extractor.]*  
*Finally, we have the **AI Chat Extractor**. Sellers can paste raw, mixed Bangla/Banglish customer chats here. Our backend uses Google Gemini with a strict substring-verification guard that guarantees zero invented or hallucinated data."*

---

### [3:55 - 4:40] Real Challenges & Engineering Decisions (45s)
*"Building this came with real engineering challenges.*  
*One big challenge was **Bangla digit and phone normalization**. Customers type mixed Bangla and English numerals and various prefixes like '+880' or '01'. I wrote regex normalization rules to sanitize these without guessing.*  
*Another challenge was **financial precision**. In JavaScript, floating-point math can lead to rounding errors, so every price in this system is computed strictly in integer paisa.*  
*And on the frontend, I chose **vanilla ES Modules with zero build tools**. This avoids client-side JavaScript bloat so the checkout page loads in milliseconds even on a weak 3G mobile connection in rural Bangladesh."*

---

### [4:40 - 5:00] Closing & Next Steps (20s)
*"The next step for this project is direct API integration with Bangladeshi couriers like Steadfast and Pathao for automated consignment booking, followed by pilot testing with real boutique shops in Dhaka.*  
*Thank you for watching, and I look forward to discussing the code with the Credosis team!"*

---

## 🎬 Step-by-Step Recording Playbook

Follow these exact physical steps during your screen recording:

1. **Start on Desktop (`/`)**: Show the login screen. Say intro.
2. **Click "⚡ Fill Demo Key"**: Log in smoothly without typing.
3. **Select Draft Order**: Point out line items.
4. **Generate Link**: Click "Create checkout link" $\rightarrow$ Click "Copy".
5. **Switch to Mobile Tab (`/buy/<token>`)**: Show responsive card, bilingual text, fill name/phone/address, click "Confirm Order".
6. **Show Tracking Page (`/track/<token>`)**: Point out green checkmark and tracking timeline.
7. **Switch back to Dashboard**: Show order status changed to `confirmed`.
8. **Advance Status to `shipped`**: Enter courier name and tracking code $\rightarrow$ save.
9. **Expand Catalog**: Show stock count and low-stock badge.
10. **Open Extractor**: Paste sample chat $\rightarrow$ show AI extraction draft.
11. **Close**: Speak to challenges and next steps with confidence.

