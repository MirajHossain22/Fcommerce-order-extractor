# Evaluation results

Run time (UTC): 2026-10-28T13:14:45.221452+00:00
Provider: local
Model: regex-baseline
Dataset: dataset.jsonl
Messages: 50
Extraction errors: 0

Overall accuracy (all 7 fields exact): 46.00% (23/50)
Mean field accuracy: 83.43%

| Field | Correct / total | Accuracy |
| --- | --- | --- |
| is_order | 47 / 50 | 94.00% |
| customer_name | 31 / 50 | 62.00% |
| phone | 47 / 50 | 94.00% |
| address | 31 / 50 | 62.00% |
| product | 41 / 50 | 82.00% |
| quantity | 45 / 50 | 90.00% |
| notes | 50 / 50 | 100.00% |

Exact comparison includes nulls and non-orders. Warnings are not scored.
Extraction errors count as incorrect for all fields; they are never omitted from denominators.
Provider errors affect these end-to-end scores, so they are not pure model-accuracy measurements.

## Failures

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
  "actual": {
    "is_order": true,
    "customer_name": "TEST_CUSTOMER_002",
    "phone": null,
    "address": "TEST_ADDRESS_002",
    "product": "Samsung Galaxy A15 phone cover",
    "quantity": 1,
    "notes": null
  },
  "mismatched_fields": [
    "phone"
  ]
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
  "actual": {
    "is_order": true,
    "customer_name": null,
    "phone": "01600000003",
    "address": null,
    "product": "Red Jamdani Saree",
    "quantity": 3,
    "notes": null
  },
  "mismatched_fields": [
    "customer_name",
    "address"
  ]
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
  "actual": {
    "is_order": true,
    "customer_name": "TEST_CUSTOMER_005",
    "phone": "01300000005",
    "address": "TEST_ADDRESS_005",
    "product": null,
    "quantity": 2,
    "notes": null
  },
  "mismatched_fields": [
    "product"
  ]
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
  "actual": {
    "is_order": true,
    "customer_name": "TEST_CUSTOMER_007",
    "phone": "01800000007",
    "address": "TEST_ADDRESS_007",
    "product": null,
    "quantity": null,
    "notes": null
  },
  "mismatched_fields": [
    "product",
    "quantity"
  ]
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
  "actual": {
    "is_order": true,
    "customer_name": null,
    "phone": "01900000008",
    "address": "TEST_ADDRESS_008",
    "product": "White School Bag",
    "quantity": 2,
    "notes": null
  },
  "mismatched_fields": [
    "customer_name"
  ]
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
  "actual": {
    "is_order": false,
    "customer_name": null,
    "phone": null,
    "address": null,
    "product": null,
    "quantity": null,
    "notes": null
  },
  "mismatched_fields": [
    "is_order",
    "customer_name",
    "phone",
    "address",
    "product",
    "quantity"
  ]
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
  "actual": {
    "is_order": true,
    "customer_name": null,
    "phone": "01300000011",
    "address": null,
    "product": "Men Running Shoes size 42",
    "quantity": 2,
    "notes": null
  },
  "mismatched_fields": [
    "customer_name",
    "address"
  ]
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
  "actual": {
    "is_order": true,
    "customer_name": null,
    "phone": "01800000013",
    "address": null,
    "product": null,
    "quantity": null,
    "notes": null
  },
  "mismatched_fields": [
    "customer_name",
    "address",
    "product",
    "quantity"
  ]
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
  "actual": {
    "is_order": false,
    "customer_name": null,
    "phone": null,
    "address": null,
    "product": null,
    "quantity": null,
    "notes": null
  },
  "mismatched_fields": [
    "is_order",
    "customer_name",
    "phone",
    "address",
    "product",
    "quantity"
  ]
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
  "actual": {
    "is_order": true,
    "customer_name": "TEST_CUSTOMER_016",
    "phone": "01500000016",
    "address": "TEST_ADDRESS_016, 2 ta",
    "product": null,
    "quantity": 2,
    "notes": null
  },
  "mismatched_fields": [
    "address"
  ]
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
  "actual": {
    "is_order": true,
    "customer_name": "TEST_CUSTOMER_017",
    "phone": "01300000017",
    "address": null,
    "product": "black panjabi",
    "quantity": 1,
    "notes": null
  },
  "mismatched_fields": [
    "address"
  ]
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
  "actual": {
    "is_order": true,
    "customer_name": null,
    "phone": "01700000018",
    "address": null,
    "product": "shirt",
    "quantity": 3,
    "notes": null
  },
  "mismatched_fields": [
    "customer_name",
    "address"
  ]
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
  "actual": {
    "is_order": true,
    "customer_name": null,
    "phone": "01800000019",
    "address": null,
    "product": "lal saree",
    "quantity": 2,
    "notes": null
  },
  "mismatched_fields": [
    "customer_name",
    "address"
  ]
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
  "actual": {
    "is_order": true,
    "customer_name": null,
    "phone": "01900000020",
    "address": null,
    "product": "lagbe pls",
    "quantity": 1,
    "notes": null
  },
  "mismatched_fields": [
    "customer_name",
    "address",
    "product"
  ]
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
  "actual": {
    "is_order": true,
    "customer_name": "TEST_CUSTOMER_022",
    "phone": "01500000022",
    "address": "TEST_ADDRESS_022",
    "product": "nibo",
    "quantity": 2,
    "notes": null
  },
  "mismatched_fields": [
    "product"
  ]
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
  "actual": {
    "is_order": true,
    "customer_name": null,
    "phone": "01300000023",
    "address": null,
    "product": "jeans pant (32 size)",
    "quantity": 1,
    "notes": null
  },
  "mismatched_fields": [
    "customer_name",
    "address"
  ]
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
  "actual": {
    "is_order": true,
    "customer_name": null,
    "phone": "01700000024",
    "address": null,
    "product": "white tshirt",
    "quantity": 5,
    "notes": null
  },
  "mismatched_fields": [
    "customer_name",
    "address"
  ]
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
  "actual": {
    "is_order": true,
    "customer_name": null,
    "phone": "01800000025",
    "address": null,
    "product": "cap",
    "quantity": 3,
    "notes": null
  },
  "mismatched_fields": [
    "customer_name",
    "address"
  ]
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
  "actual": {
    "is_order": true,
    "customer_name": null,
    "phone": "01900000026",
    "address": null,
    "product": "power bank 10000mah",
    "quantity": 1,
    "notes": null
  },
  "mismatched_fields": [
    "customer_name",
    "address"
  ]
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
  "actual": {
    "is_order": true,
    "customer_name": null,
    "phone": "01500000028",
    "address": "TEST_ADDRESS_028",
    "product": "ladies bag",
    "quantity": 1,
    "notes": null
  },
  "mismatched_fields": [
    "customer_name"
  ]
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
  "actual": {
    "is_order": true,
    "customer_name": null,
    "phone": "01300000029",
    "address": null,
    "product": "pen",
    "quantity": 12,
    "notes": null
  },
  "mismatched_fields": [
    "customer_name",
    "address"
  ]
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
  "actual": {
    "is_order": true,
    "customer_name": "TEST_CUSTOMER_030",
    "phone": "01700000030",
    "address": null,
    "product": "water bottle (1 litre)",
    "quantity": 1,
    "notes": null
  },
  "mismatched_fields": [
    "address"
  ]
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
  "actual": {
    "is_order": true,
    "customer_name": null,
    "phone": "01900000038",
    "address": null,
    "product": "কুর্তি",
    "quantity": 2,
    "notes": null
  },
  "mismatched_fields": [
    "customer_name",
    "address"
  ]
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
  "actual": {
    "is_order": false,
    "customer_name": null,
    "phone": null,
    "address": null,
    "product": null,
    "quantity": null,
    "notes": null
  },
  "mismatched_fields": [
    "is_order",
    "customer_name",
    "address",
    "product",
    "quantity"
  ]
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
  "actual": {
    "is_order": true,
    "customer_name": "TEST_CUSTOMER_043",
    "phone": "01800000043",
    "address": "TEST_ADDRESS_043",
    "product": null,
    "quantity": null,
    "notes": null
  },
  "mismatched_fields": [
    "product"
  ]
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
  "actual": {
    "is_order": true,
    "customer_name": null,
    "phone": null,
    "address": "TEST_ADDRESS_044",
    "product": "cap",
    "quantity": 2,
    "notes": null
  },
  "mismatched_fields": [
    "customer_name"
  ]
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
  "actual": {
    "is_order": true,
    "customer_name": null,
    "phone": "01600000045",
    "address": null,
    "product": null,
    "quantity": null,
    "notes": null
  },
  "mismatched_fields": [
    "customer_name",
    "address"
  ]
}
```
