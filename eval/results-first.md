# Evaluation results

This first live run produced 50 extraction errors and no usable predictions. The 0% scores below measure failed end-to-end requests, not model prediction accuracy.

A separate diagnostic request after this run returned HTTP 429 (`RESOURCE_EXHAUSTED`): the provider reported that the free-tier daily request limit of 20 for `gemini-3.8-flash` was exhausted. Individual error causes were not retained by the evaluator, so this diagnostic does not establish the cause of every earlier failure.

Run time (UTC): 2026-10-26T21:11:03.435495+00:00
Provider: gemini
Model: gemini-3.8-flash
Dataset: dataset.jsonl
Messages: 50
Extraction errors: 50

Overall accuracy (all 7 fields exact): 0.00% (0/50)
Mean field accuracy: 0.00%

| Field | Correct / total | Accuracy |
| --- | --- | --- |
| is_order | 0 / 50 | 0.00% |
| customer_name | 0 / 50 | 0.00% |
| phone | 0 / 50 | 0.00% |
| address | 0 / 50 | 0.00% |
| product | 0 / 50 | 0.00% |
| quantity | 0 / 50 | 0.00% |
| notes | 0 / 50 | 0.00% |

Exact comparison includes nulls and non-orders. Warnings are not scored.
Extraction errors count as incorrect for all fields; they are never omitted from denominators.
Provider errors affect these end-to-end scores, so they are not pure model-accuracy measurements.

## Failures

### Case 1

```json
{
  "case": 1,
  "id": "msg_001",
  "category": "clean",
  "message": "Hi, I want to order 2 pcs Blue Cotton Panjabi. Name: TEST_CUSTOMER_001, Phone: 01800000001, Address: TEST_ADDRESS_001.",
  "expected": {
    "is_order": true,
    "customer_name": "TEST_CUSTOMER_001",
    "phone": "01800000001",
    "address": "TEST_ADDRESS_001",
    "product": "Blue Cotton Panjabi",
    "quantity": 2,
    "notes": null
  },
  "actual": null,
  "error": "Extraction failed; all fields counted as incorrect."
}
```

### Case 2

```json
{
  "case": 2,
  "id": "msg_002",
  "category": "clean",
  "message": "Order: 1 Samsung Galaxy A15 phone cover. Name: TEST_CUSTOMER_002. Mobile: 01900000002. Address: TEST_ADDRESS_002.",
  "expected": {
    "is_order": true,
    "customer_name": "TEST_CUSTOMER_002",
    "phone": "01900000002",
    "address": "TEST_ADDRESS_002",
    "product": "Samsung Galaxy A15 phone cover",
    "quantity": 1,
    "notes": null
  },
  "actual": null,
  "error": "Extraction failed; all fields counted as incorrect."
}
```

### Case 3

```json
{
  "case": 3,
  "id": "msg_003",
  "category": "clean",
  "message": "Please send 3 Red Jamdani Saree to TEST_CUSTOMER_003, 01600000003, TEST_ADDRESS_003.",
  "expected": {
    "is_order": true,
    "customer_name": "TEST_CUSTOMER_003",
    "phone": "01600000003",
    "address": "TEST_ADDRESS_003",
    "product": "Red Jamdani Saree",
    "quantity": 3,
    "notes": null
  },
  "actual": null,
  "error": "Extraction failed; all fields counted as incorrect."
}
```

### Case 4

```json
{
  "case": 4,
  "id": "msg_004",
  "category": "clean",
  "message": "I would like to buy 5 Premium Basmati Rice. Name TEST_CUSTOMER_004, number 01500000004, address TEST_ADDRESS_004.",
  "expected": {
    "is_order": true,
    "customer_name": "TEST_CUSTOMER_004",
    "phone": "01500000004",
    "address": "TEST_ADDRESS_004",
    "product": "Premium Basmati Rice",
    "quantity": 5,
    "notes": null
  },
  "actual": null,
  "error": "Extraction failed; all fields counted as incorrect."
}
```

### Case 5

```json
{
  "case": 5,
  "id": "msg_005",
  "category": "clean",
  "message": "Order confirm: Black Leather Wallet x2. Customer: TEST_CUSTOMER_005. Phone: 01300000005. Delivery address: TEST_ADDRESS_005.",
  "expected": {
    "is_order": true,
    "customer_name": "TEST_CUSTOMER_005",
    "phone": "01300000005",
    "address": "TEST_ADDRESS_005",
    "product": "Black Leather Wallet",
    "quantity": 2,
    "notes": null
  },
  "actual": null,
  "error": "Extraction failed; all fields counted as incorrect."
}
```

### Case 6

```json
{
  "case": 6,
  "id": "msg_006",
  "category": "clean",
  "message": "Name: TEST_CUSTOMER_006\nPhone: 01700000006\nAddress: TEST_ADDRESS_006\nProduct: Herbal Hair Oil 200ml\nQuantity: 4",
  "expected": {
    "is_order": true,
    "customer_name": "TEST_CUSTOMER_006",
    "phone": "01700000006",
    "address": "TEST_ADDRESS_006",
    "product": "Herbal Hair Oil 200ml",
    "quantity": 4,
    "notes": null
  },
  "actual": null,
  "error": "Extraction failed; all fields counted as incorrect."
}
```

### Case 7

```json
{
  "case": 7,
  "id": "msg_007",
  "category": "clean",
  "message": "Hello, 1 Wireless Earbuds Pro lagbe. Name TEST_CUSTOMER_007, phone 01800000007, address TEST_ADDRESS_007.",
  "expected": {
    "is_order": true,
    "customer_name": "TEST_CUSTOMER_007",
    "phone": "01800000007",
    "address": "TEST_ADDRESS_007",
    "product": "Wireless Earbuds Pro",
    "quantity": 1,
    "notes": null
  },
  "actual": null,
  "error": "Extraction failed; all fields counted as incorrect."
}
```

### Case 8

```json
{
  "case": 8,
  "id": "msg_008",
  "category": "clean",
  "message": "Please deliver 2 White School Bag to TEST_CUSTOMER_008. Contact: 01900000008. Address: TEST_ADDRESS_008.",
  "expected": {
    "is_order": true,
    "customer_name": "TEST_CUSTOMER_008",
    "phone": "01900000008",
    "address": "TEST_ADDRESS_008",
    "product": "White School Bag",
    "quantity": 2,
    "notes": null
  },
  "actual": null,
  "error": "Extraction failed; all fields counted as incorrect."
}
```

### Case 9

```json
{
  "case": 9,
  "id": "msg_009",
  "category": "clean",
  "message": "I want 6 Cotton Hijab. Name: TEST_CUSTOMER_009, Phone: 01600000009, Address: TEST_ADDRESS_009.",
  "expected": {
    "is_order": true,
    "customer_name": "TEST_CUSTOMER_009",
    "phone": "01600000009",
    "address": "TEST_ADDRESS_009",
    "product": "Cotton Hijab",
    "quantity": 6,
    "notes": null
  },
  "actual": null,
  "error": "Extraction failed; all fields counted as incorrect."
}
```

### Case 10

```json
{
  "case": 10,
  "id": "msg_010",
  "category": "clean",
  "message": "Order 1 Gaming Mouse RGB. Name: TEST_CUSTOMER_010. Phone: 01500000010. Address: TEST_ADDRESS_010.",
  "expected": {
    "is_order": true,
    "customer_name": "TEST_CUSTOMER_010",
    "phone": "01500000010",
    "address": "TEST_ADDRESS_010",
    "product": "Gaming Mouse RGB",
    "quantity": 1,
    "notes": null
  },
  "actual": null,
  "error": "Extraction failed; all fields counted as incorrect."
}
```

### Case 11

```json
{
  "case": 11,
  "id": "msg_011",
  "category": "clean",
  "message": "Send 2 Men Running Shoes size 42 to TEST_CUSTOMER_011, 01300000011, TEST_ADDRESS_011.",
  "expected": {
    "is_order": true,
    "customer_name": "TEST_CUSTOMER_011",
    "phone": "01300000011",
    "address": "TEST_ADDRESS_011",
    "product": "Men Running Shoes size 42",
    "quantity": 2,
    "notes": null
  },
  "actual": null,
  "error": "Extraction failed; all fields counted as incorrect."
}
```

### Case 12

```json
{
  "case": 12,
  "id": "msg_012",
  "category": "clean",
  "message": "Name: TEST_CUSTOMER_012, Phone: 01700000012, Address: TEST_ADDRESS_012, Product: Kids Winter Jacket, Qty: 3",
  "expected": {
    "is_order": true,
    "customer_name": "TEST_CUSTOMER_012",
    "phone": "01700000012",
    "address": "TEST_ADDRESS_012",
    "product": "Kids Winter Jacket",
    "quantity": 3,
    "notes": null
  },
  "actual": null,
  "error": "Extraction failed; all fields counted as incorrect."
}
```

### Case 13

```json
{
  "case": 13,
  "id": "msg_013",
  "category": "clean",
  "message": "Order for TEST_CUSTOMER_013: 1 Mechanical Keyboard, number 01800000013, deliver to TEST_ADDRESS_013.",
  "expected": {
    "is_order": true,
    "customer_name": "TEST_CUSTOMER_013",
    "phone": "01800000013",
    "address": "TEST_ADDRESS_013",
    "product": "Mechanical Keyboard",
    "quantity": 1,
    "notes": null
  },
  "actual": null,
  "error": "Extraction failed; all fields counted as incorrect."
}
```

### Case 14

```json
{
  "case": 14,
  "id": "msg_014",
  "category": "clean",
  "message": "I need 10 Handmade Soap Bar. Name TEST_CUSTOMER_014, phone 01900000014, address TEST_ADDRESS_014.",
  "expected": {
    "is_order": true,
    "customer_name": "TEST_CUSTOMER_014",
    "phone": "01900000014",
    "address": "TEST_ADDRESS_014",
    "product": "Handmade Soap Bar",
    "quantity": 10,
    "notes": null
  },
  "actual": null,
  "error": "Extraction failed; all fields counted as incorrect."
}
```

### Case 15

```json
{
  "case": 15,
  "id": "msg_015",
  "category": "clean",
  "message": "Please book 2 Mustard Oil 5L. Name: TEST_CUSTOMER_015. Phone 01600000015. Address: TEST_ADDRESS_015.",
  "expected": {
    "is_order": true,
    "customer_name": "TEST_CUSTOMER_015",
    "phone": "01600000015",
    "address": "TEST_ADDRESS_015",
    "product": "Mustard Oil 5L",
    "quantity": 2,
    "notes": null
  },
  "actual": null,
  "error": "Extraction failed; all fields counted as incorrect."
}
```

### Case 16

```json
{
  "case": 16,
  "id": "msg_016",
  "category": "messy",
  "message": "bhai ei product ta lagbe, address: TEST_ADDRESS_016, 2 ta, number 01500000016, naam TEST_CUSTOMER_016",
  "expected": {
    "is_order": true,
    "customer_name": "TEST_CUSTOMER_016",
    "phone": "01500000016",
    "address": "TEST_ADDRESS_016",
    "product": null,
    "quantity": 2,
    "notes": null
  },
  "actual": null,
  "error": "Extraction failed; all fields counted as incorrect."
}
```

### Case 17

```json
{
  "case": 17,
  "id": "msg_017",
  "category": "messy",
  "message": "apu 1ta black panjabi chai, naam TEST_CUSTOMER_017, 01300000017, TEST_ADDRESS_017",
  "expected": {
    "is_order": true,
    "customer_name": "TEST_CUSTOMER_017",
    "phone": "01300000017",
    "address": "TEST_ADDRESS_017",
    "product": "black panjabi",
    "quantity": 1,
    "notes": null
  },
  "actual": null,
  "error": "Extraction failed; all fields counted as incorrect."
}
```

### Case 18

```json
{
  "case": 18,
  "id": "msg_018",
  "category": "messy",
  "message": "vai 3 ta shirt pathai den. TEST_CUSTOMER_018, 017-00000018. TEST_ADDRESS_018",
  "expected": {
    "is_order": true,
    "customer_name": "TEST_CUSTOMER_018",
    "phone": "01700000018",
    "address": "TEST_ADDRESS_018",
    "product": "shirt",
    "quantity": 3,
    "notes": null
  },
  "actual": null,
  "error": "Extraction failed; all fields counted as incorrect."
}
```

### Case 19

```json
{
  "case": 19,
  "id": "msg_019",
  "category": "messy",
  "message": "ami duita lal saree nibo. TEST_CUSTOMER_019. 01800000019. TEST_ADDRESS_019",
  "expected": {
    "is_order": true,
    "customer_name": "TEST_CUSTOMER_019",
    "phone": "01800000019",
    "address": "TEST_ADDRESS_019",
    "product": "lal saree",
    "quantity": 2,
    "notes": null
  },
  "actual": null,
  "error": "Extraction failed; all fields counted as incorrect."
}
```

### Case 20

```json
{
  "case": 20,
  "id": "msg_020",
  "category": "messy",
  "message": "sis ei bag ta ekta lagbe pls, TEST_CUSTOMER_020, +8801900000020, TEST_ADDRESS_020",
  "expected": {
    "is_order": true,
    "customer_name": "TEST_CUSTOMER_020",
    "phone": "01900000020",
    "address": "TEST_ADDRESS_020",
    "product": "bag",
    "quantity": 1,
    "notes": null
  },
  "actual": null,
  "error": "Extraction failed; all fields counted as incorrect."
}
```

### Case 21

```json
{
  "case": 21,
  "id": "msg_021",
  "category": "messy",
  "message": "bhaiya 4 pcs mug order korbo, name: TEST_CUSTOMER_021, ph 01600000021, add: TEST_ADDRESS_021",
  "expected": {
    "is_order": true,
    "customer_name": "TEST_CUSTOMER_021",
    "phone": "01600000021",
    "address": "TEST_ADDRESS_021",
    "product": "mug",
    "quantity": 4,
    "notes": null
  },
  "actual": null,
  "error": "Extraction failed; all fields counted as incorrect."
}
```

### Case 22

```json
{
  "case": 22,
  "id": "msg_022",
  "category": "messy",
  "message": "hello vai, charger ta 2ta nibo. address TEST_ADDRESS_022, number 01500000022, naam TEST_CUSTOMER_022",
  "expected": {
    "is_order": true,
    "customer_name": "TEST_CUSTOMER_022",
    "phone": "01500000022",
    "address": "TEST_ADDRESS_022",
    "product": "charger",
    "quantity": 2,
    "notes": null
  },
  "actual": null,
  "error": "Extraction failed; all fields counted as incorrect."
}
```

### Case 23

```json
{
  "case": 23,
  "id": "msg_023",
  "category": "messy",
  "message": "order korte chai 1 ta jeans pant (32 size). TEST_CUSTOMER_023 880 1300000023 TEST_ADDRESS_023",
  "expected": {
    "is_order": true,
    "customer_name": "TEST_CUSTOMER_023",
    "phone": "01300000023",
    "address": "TEST_ADDRESS_023",
    "product": "jeans pant (32 size)",
    "quantity": 1,
    "notes": null
  },
  "actual": null,
  "error": "Extraction failed; all fields counted as incorrect."
}
```

### Case 24

```json
{
  "case": 24,
  "id": "msg_024",
  "category": "messy",
  "message": "ami 5ta white tshirt lagbe, TEST_CUSTOMER_024, 01700000024, TEST_ADDRESS_024",
  "expected": {
    "is_order": true,
    "customer_name": "TEST_CUSTOMER_024",
    "phone": "01700000024",
    "address": "TEST_ADDRESS_024",
    "product": "white tshirt",
    "quantity": 5,
    "notes": null
  },
  "actual": null,
  "error": "Extraction failed; all fields counted as incorrect."
}
```

### Case 25

```json
{
  "case": 25,
  "id": "msg_025",
  "category": "messy",
  "message": "vai 3 ta cap chai, TEST_CUSTOMER_025, +8801800000025, TEST_ADDRESS_025",
  "expected": {
    "is_order": true,
    "customer_name": "TEST_CUSTOMER_025",
    "phone": "01800000025",
    "address": "TEST_ADDRESS_025",
    "product": "cap",
    "quantity": 3,
    "notes": null
  },
  "actual": null,
  "error": "Extraction failed; all fields counted as incorrect."
}
```

### Case 26

```json
{
  "case": 26,
  "id": "msg_026",
  "category": "messy",
  "message": "Order dibo 1ta power bank 10000mah. TEST_CUSTOMER_026. 01900000026. TEST_ADDRESS_026",
  "expected": {
    "is_order": true,
    "customer_name": "TEST_CUSTOMER_026",
    "phone": "01900000026",
    "address": "TEST_ADDRESS_026",
    "product": "power bank 10000mah",
    "quantity": 1,
    "notes": null
  },
  "actual": null,
  "error": "Extraction failed; all fields counted as incorrect."
}
```

### Case 27

```json
{
  "case": 27,
  "id": "msg_027",
  "category": "messy",
  "message": "bro 2 pis headphone lagbe, address TEST_ADDRESS_027, naam: TEST_CUSTOMER_027, phn 016-00000027",
  "expected": {
    "is_order": true,
    "customer_name": "TEST_CUSTOMER_027",
    "phone": "01600000027",
    "address": "TEST_ADDRESS_027",
    "product": "headphone",
    "quantity": 2,
    "notes": null
  },
  "actual": null,
  "error": "Extraction failed; all fields counted as incorrect."
}
```

### Case 28

```json
{
  "case": 28,
  "id": "msg_028",
  "category": "messy",
  "message": "vaiya ekta ladies bag lagbe, ami TEST_CUSTOMER_028, number 01500000028, address: TEST_ADDRESS_028",
  "expected": {
    "is_order": true,
    "customer_name": "TEST_CUSTOMER_028",
    "phone": "01500000028",
    "address": "TEST_ADDRESS_028",
    "product": "ladies bag",
    "quantity": 1,
    "notes": null
  },
  "actual": null,
  "error": "Extraction failed; all fields counted as incorrect."
}
```

### Case 29

```json
{
  "case": 29,
  "id": "msg_029",
  "category": "messy",
  "message": "assalamualaikum, 12 ta pen nibo school er jonno, TEST_CUSTOMER_029, 01300000029, TEST_ADDRESS_029",
  "expected": {
    "is_order": true,
    "customer_name": "TEST_CUSTOMER_029",
    "phone": "01300000029",
    "address": "TEST_ADDRESS_029",
    "product": "pen",
    "quantity": 12,
    "notes": null
  },
  "actual": null,
  "error": "Extraction failed; all fields counted as incorrect."
}
```

### Case 30

```json
{
  "case": 30,
  "id": "msg_030",
  "category": "messy",
  "message": "bhai amar 1 ta water bottle (1 litre) lagbe, naam TEST_CUSTOMER_030, 01700000030, TEST_ADDRESS_030",
  "expected": {
    "is_order": true,
    "customer_name": "TEST_CUSTOMER_030",
    "phone": "01700000030",
    "address": "TEST_ADDRESS_030",
    "product": "water bottle (1 litre)",
    "quantity": 1,
    "notes": null
  },
  "actual": null,
  "error": "Extraction failed; all fields counted as incorrect."
}
```

### Case 31

```json
{
  "case": 31,
  "id": "msg_031",
  "category": "mixed",
  "message": "আমি ২টা নীল পাঞ্জাবি নিব। নাম: পরীক্ষা_ক্রেতা_031, ফোন: ০১৮০০০০০০৩১, ঠিকানা: পরীক্ষা_ঠিকানা_031",
  "expected": {
    "is_order": true,
    "customer_name": "পরীক্ষা_ক্রেতা_031",
    "phone": "01800000031",
    "address": "পরীক্ষা_ঠিকানা_031",
    "product": "নীল পাঞ্জাবি",
    "quantity": 2,
    "notes": null
  },
  "actual": null,
  "error": "Extraction failed; all fields counted as incorrect."
}
```

### Case 32

```json
{
  "case": 32,
  "id": "msg_032",
  "category": "mixed",
  "message": "ভাই ১টা ব্লুটুথ স্পীকার লাগবে। আমার নাম পরীক্ষা_ক্রেতা_032, নাম্বার ০১৯০০০০০০৩২, ঠিকানা: পরীক্ষা_ঠিকানা_032",
  "expected": {
    "is_order": true,
    "customer_name": "পরীক্ষা_ক্রেতা_032",
    "phone": "01900000032",
    "address": "পরীক্ষা_ঠিকানা_032",
    "product": "ব্লুটুথ স্পীকার",
    "quantity": 1,
    "notes": null
  },
  "actual": null,
  "error": "Extraction failed; all fields counted as incorrect."
}
```

### Case 33

```json
{
  "case": 33,
  "id": "msg_033",
  "category": "mixed",
  "message": "আপু 3 pcs লিপস্টিক অর্ডার করবো, নাম পরীক্ষা_ক্রেতা_033, ফোন 01600000033, ঠিকানা পরীক্ষা_ঠিকানা_033",
  "expected": {
    "is_order": true,
    "customer_name": "পরীক্ষা_ক্রেতা_033",
    "phone": "01600000033",
    "address": "পরীক্ষা_ঠিকানা_033",
    "product": "লিপস্টিক",
    "quantity": 3,
    "notes": null
  },
  "actual": null,
  "error": "Extraction failed; all fields counted as incorrect."
}
```

### Case 34

```json
{
  "case": 34,
  "id": "msg_034",
  "category": "mixed",
  "message": "Vai ekta পাঞ্জাবি lagbe. Name: TEST_CUSTOMER_034, Phone 01500000034, Address: পরীক্ষা_ঠিকানা_034",
  "expected": {
    "is_order": true,
    "customer_name": "TEST_CUSTOMER_034",
    "phone": "01500000034",
    "address": "পরীক্ষা_ঠিকানা_034",
    "product": "পাঞ্জাবি",
    "quantity": 1,
    "notes": null
  },
  "actual": null,
  "error": "Extraction failed; all fields counted as incorrect."
}
```

### Case 35

```json
{
  "case": 35,
  "id": "msg_035",
  "category": "mixed",
  "message": "Order: ২ টা Hijab, নাম: TEST_CUSTOMER_035, মোবাইল: 01300000035, address: পরীক্ষা_ঠিকানা_035",
  "expected": {
    "is_order": true,
    "customer_name": "TEST_CUSTOMER_035",
    "phone": "01300000035",
    "address": "পরীক্ষা_ঠিকানা_035",
    "product": "Hijab",
    "quantity": 2,
    "notes": null
  },
  "actual": null,
  "error": "Extraction failed; all fields counted as incorrect."
}
```

### Case 36

```json
{
  "case": 36,
  "id": "msg_036",
  "category": "mixed",
  "message": "bhaiya আমার ৪টা মগ লাগবে, naam TEST_CUSTOMER_036, number 017-00000036, ঠিকানা পরীক্ষা_ঠিকানা_036",
  "expected": {
    "is_order": true,
    "customer_name": "TEST_CUSTOMER_036",
    "phone": "01700000036",
    "address": "পরীক্ষা_ঠিকানা_036",
    "product": "মগ",
    "quantity": 4,
    "notes": null
  },
  "actual": null,
  "error": "Extraction failed; all fields counted as incorrect."
}
```

### Case 37

```json
{
  "case": 37,
  "id": "msg_037",
  "category": "mixed",
  "message": "সালাম, ১ পিস ঘড়ি নিব। নাম পরীক্ষা_ক্রেতা_037, নং +8801800000037, ঠিকানা: পরীক্ষা_ঠিকানা_037",
  "expected": {
    "is_order": true,
    "customer_name": "পরীক্ষা_ক্রেতা_037",
    "phone": "01800000037",
    "address": "পরীক্ষা_ঠিকানা_037",
    "product": "ঘড়ি",
    "quantity": 1,
    "notes": null
  },
  "actual": null,
  "error": "Extraction failed; all fields counted as incorrect."
}
```

### Case 38

```json
{
  "case": 38,
  "id": "msg_038",
  "category": "mixed",
  "message": "Hello, আমি 2 ta কুর্তি order করতে চাই। TEST_CUSTOMER_038, 01900000038, TEST_ADDRESS_038",
  "expected": {
    "is_order": true,
    "customer_name": "TEST_CUSTOMER_038",
    "phone": "01900000038",
    "address": "TEST_ADDRESS_038",
    "product": "কুর্তি",
    "quantity": 2,
    "notes": null
  },
  "actual": null,
  "error": "Extraction failed; all fields counted as incorrect."
}
```

### Case 39

```json
{
  "case": 39,
  "id": "msg_039",
  "category": "mixed",
  "message": "ভাই ৫টা চার্জার ক্যাবল দিন, address: পরীক্ষা_ঠিকানা_039, নাম: পরীক্ষা_ক্রেতা_039, ফোন ০১৬০০০০০০৩৯",
  "expected": {
    "is_order": true,
    "customer_name": "পরীক্ষা_ক্রেতা_039",
    "phone": "01600000039",
    "address": "পরীক্ষা_ঠিকানা_039",
    "product": "চার্জার ক্যাবল",
    "quantity": 5,
    "notes": null
  },
  "actual": null,
  "error": "Extraction failed; all fields counted as incorrect."
}
```

### Case 40

```json
{
  "case": 40,
  "id": "msg_040",
  "category": "mixed",
  "message": "Order dite chai: ১টা জুতা (size 41). Name TEST_CUSTOMER_040, 01500000040, ঠিকানা: পরীক্ষা_ঠিকানা_040",
  "expected": {
    "is_order": true,
    "customer_name": "TEST_CUSTOMER_040",
    "phone": "01500000040",
    "address": "পরীক্ষা_ঠিকানা_040",
    "product": "জুতা (size 41)",
    "quantity": 1,
    "notes": null
  },
  "actual": null,
  "error": "Extraction failed; all fields counted as incorrect."
}
```

### Case 41

```json
{
  "case": 41,
  "id": "msg_041",
  "category": "missing",
  "message": "Name: TEST_CUSTOMER_041, 2 pcs Panjabi, address TEST_ADDRESS_041",
  "expected": {
    "is_order": true,
    "customer_name": "TEST_CUSTOMER_041",
    "phone": null,
    "address": "TEST_ADDRESS_041",
    "product": "Panjabi",
    "quantity": 2,
    "notes": null
  },
  "actual": null,
  "error": "Extraction failed; all fields counted as incorrect."
}
```

### Case 42

```json
{
  "case": 42,
  "id": "msg_042",
  "category": "missing",
  "message": "vai 3ta shirt lagbe, phone 01700000042",
  "expected": {
    "is_order": true,
    "customer_name": null,
    "phone": "01700000042",
    "address": null,
    "product": "shirt",
    "quantity": 3,
    "notes": null
  },
  "actual": null,
  "error": "Extraction failed; all fields counted as incorrect."
}
```

### Case 43

```json
{
  "case": 43,
  "id": "msg_043",
  "category": "missing",
  "message": "I want to order Blue Cotton Saree, Name TEST_CUSTOMER_043, phone 01800000043, address TEST_ADDRESS_043",
  "expected": {
    "is_order": true,
    "customer_name": "TEST_CUSTOMER_043",
    "phone": "01800000043",
    "address": "TEST_ADDRESS_043",
    "product": "Blue Cotton Saree",
    "quantity": null,
    "notes": null
  },
  "actual": null,
  "error": "Extraction failed; all fields counted as incorrect."
}
```

### Case 44

```json
{
  "case": 44,
  "id": "msg_044",
  "category": "missing",
  "message": "vai 2 ta cap chai, TEST_CUSTOMER_044, phone 017000045, address TEST_ADDRESS_044",
  "expected": {
    "is_order": true,
    "customer_name": "TEST_CUSTOMER_044",
    "phone": null,
    "address": "TEST_ADDRESS_044",
    "product": "cap",
    "quantity": 2,
    "notes": null
  },
  "actual": null,
  "error": "Extraction failed; all fields counted as incorrect."
}
```

### Case 45

```json
{
  "case": 45,
  "id": "msg_045",
  "category": "missing",
  "message": "ami order dite chai, TEST_CUSTOMER_045, 01600000045, TEST_ADDRESS_045",
  "expected": {
    "is_order": true,
    "customer_name": "TEST_CUSTOMER_045",
    "phone": "01600000045",
    "address": "TEST_ADDRESS_045",
    "product": null,
    "quantity": null,
    "notes": null
  },
  "actual": null,
  "error": "Extraction failed; all fields counted as incorrect."
}
```

### Case 46

```json
{
  "case": 46,
  "id": "msg_046",
  "category": "non_order",
  "message": "Assalamu alaikum, apnader shop e delivery charge koto?",
  "expected": {
    "is_order": false,
    "customer_name": null,
    "phone": null,
    "address": null,
    "product": null,
    "quantity": null,
    "notes": null
  },
  "actual": null,
  "error": "Extraction failed; all fields counted as incorrect."
}
```

### Case 47

```json
{
  "case": 47,
  "id": "msg_047",
  "category": "non_order",
  "message": "ei product ta ki stock e ache?",
  "expected": {
    "is_order": false,
    "customer_name": null,
    "phone": null,
    "address": null,
    "product": null,
    "quantity": null,
    "notes": null
  },
  "actual": null,
  "error": "Extraction failed; all fields counted as incorrect."
}
```

### Case 48

```json
{
  "case": 48,
  "id": "msg_048",
  "category": "non_order",
  "message": "Thanks bhai, product ta ekdom bhalo chilo!",
  "expected": {
    "is_order": false,
    "customer_name": null,
    "phone": null,
    "address": null,
    "product": null,
    "quantity": null,
    "notes": null
  },
  "actual": null,
  "error": "Extraction failed; all fields counted as incorrect."
}
```

### Case 49

```json
{
  "case": 49,
  "id": "msg_049",
  "category": "non_order",
  "message": "পরীক্ষা শহরের বাইরে কি ডেলিভারি দেন?",
  "expected": {
    "is_order": false,
    "customer_name": null,
    "phone": null,
    "address": null,
    "product": null,
    "quantity": null,
    "notes": null
  },
  "actual": null,
  "error": "Extraction failed; all fields counted as incorrect."
}
```

### Case 50

```json
{
  "case": 50,
  "id": "msg_050",
  "category": "non_order",
  "message": "Hi, price list ta pathan please",
  "expected": {
    "is_order": false,
    "customer_name": null,
    "phone": null,
    "address": null,
    "product": null,
    "quantity": null,
    "notes": null
  },
  "actual": null,
  "error": "Extraction failed; all fields counted as incorrect."
}
```

