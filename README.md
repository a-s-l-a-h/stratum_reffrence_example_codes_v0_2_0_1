# 📱 Stratum Android Example (v0.201)

This project demonstrates running **Stratum (Python-based)** inside Android, adapted from:

https://github.com/a-s-l-a-h/stratum_v0_2_android_example

> ⚠️ Original repo uses **v0.2**  
> ✅ This setup uses **v0.201**

---

## 🚀 Setup

### 1. Clone Base Project
```bash
git clone https://github.com/a-s-l-a-h/stratum_v0_2_android_example.git
cd stratum_v0_2_android_example
````

### 2. Open in Android Studio

* Open project
* Wait for Gradle sync

### 3. Replace Python Entry

Path:

```
app/src/main/python/main.py
```

Replace with your Stratum-based code.

---

### 4. Use Stratum v0.201

```bash
git clone https://github.com/stratum-mining/stratum.git
cd stratum
git checkout v0.201
```

* Copy or integrate required modules into:

```
app/src/main/python/
```

---

### 5. Adjust Imports

* Update code for **v0.201 API**
* Fix module paths if needed

---

### 6. Run

* Build & run from Android Studio

---

## 🔄 Notes

* Base repo is for **v0.2**, this is adapted to **v0.201**
* Ensure all dependencies are included
* Use Logcat for debugging

```

