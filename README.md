## CS203 Lab Assignment 1

#### Data Collection using OpenTelemetry and Jaeger

---

**[Github repository](https://github.com/Reckadon/STT-Assignment1-DataCollection)**

**_Team Members_**
Name | Roll Number
---|---
Romit Mohane | 23110279
Rudra Pratap Singh | 23110281

---

## Features Implemented

### 1. Add Courses to the Catalog

- **Screenshot 1:** Homepage showing the **"Add a New Course"** button.  
  ![Homepage with Add Button](screenshots/screenshot1.png)

- **Screenshot 2:** Form for manually entering new course details.  
  ![Course Form](screenshots/screenshot2.png)

- **Screenshot 3:** Confirmation message after successfully adding a course.  
  ![Confirmation Message](screenshots/screenshot3.png)  
  ![Confirmation Message - Additional](screenshots/screenshot3-I.png)

- **Screenshot 4:** Error message displayed when required fields are missing.  
  ![Error Message](screenshots/screenshot4.png)

- **Screenshot 5:** Log output showing error and success messages for adding courses.  
  ![Log Output](screenshots/screenshot5.png)  
  ![Log Output - Additional](screenshots/screenshot5-I.png)

---

### 2. OpenTelemetry Tracing

- **Screenshot 6:** Tracing data for the course catalog page request.  
  ![Catalog Trace](screenshots/screenshot6.png)

- **Screenshot 7:** Tracing data for the "Add a New Course" form submission.  
  ![Form Trace](screenshots/screenshot7.png)
  ![Form Trace](screenshots/screenshot17.png)

- **Screenshot 8:** Tracing data for browsing course details.  
  ![Browsing Trace](screenshots/screenshot8.png)

- **Screenshot 9:** Spans for key operations  
   ![FOrm error](screenshots/screenshot14.jpg)
  _Form Error_
  ![Loading courses from file](screenshots/screenshot15.jpg)
  _Loading Courses data from file and rendering Catalog Page_

- **Screenshot 10:** OpenTelemetry spans with **attributes** (e.g., user IP, request methods, metadata).  
  ![Tracing Spans](screenshots/screenshot9.png)

---

### 3. Exporting Telemetry Data to Jaeger

- **Screenshot 11:** **opentelemetry.metrics.counter** showing total requests to each route and how many courses are added.  
  ![Jaeger Requests](screenshots/screenshot10.JPG)  
  ![Jaeger Requests](screenshots/screenshot10.png)  
  ![Jaeger Requests - Part I](screenshots/screenshot10-I.jpg)

- **Screenshot 12:** **opentelemetry.metrics.histogram** as well as **Jaeger dashboard** showing total processing time for each operation.  
   ![Jaeger Processing Time](screenshots/screenshot11.jpg)
  ![Jaeger Processing Time](screenshots/screenshot17.png)
  _Example of processign duration of each operation on Jaeger UI_

- **Screenshot 13:** Jaeger dashboard as well as **opentelemetry.metrics** displaying error counts for missing form fields or other issues.  
   ![Jaeger Errors](screenshots/screenshot12.jpg)
  ![Jaeger Errors](screenshots/screenshot12.png)
  _Form Error_
  ![Database Errors](screenshots/screenshot16.png)
  _File Read Error_

- **Screenshot 14:** Example of structured logging output in JSON format.  
  ![JSON Logs - Part I](screenshots/screenshot13-I.png)  
  ![JSON Logs - Part II](screenshots/screenshot13-II.png)

---

To Run:  
run the `app.py` file after installing the necessary dependencies:

- `flask`, `opentelemetry-instrumentation`, `opentelemetry-instrumentation-flask`, `opentelemetry-exporter-jaeger`
