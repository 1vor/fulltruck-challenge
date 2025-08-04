
### **Introduction**
Welcome to FullTruck! We are a pioneering digital freight network on a mission to solve one of the most critical inefficiencies in logistics: **empty miles**. Every day, countless carriers drive for hours with empty trucks after completing deliveries. This isn't just a waste of time and resources — it’s also a major contributor to CO₂ emissions and lost revenue.

At FullTruck, our goal is to **ensure that every carrier receives the right freight at the right time**. Through intelligent algorithms, thoughtful system design, and data-driven decision-making, we aim to eliminate inefficiencies and create a more sustainable, profitable, and optimized freight ecosystem.

To achieve this, we’ve built a platform designed to make shipper–carrier matching as effective as possible. One of the key elements in our platform is our **recommendation system**, which leverages carrier preferences, real-time freight availability, and historical trends to suggest the most suitable loads for each carrier.

A crucial part of this system is the **storing of freight searches** — structured representations of carrier intent that describe their preferred lanes, price expectations, and availability. These searches are what enable us to anticipate carrier needs and proactively match them with opportunities, reducing downtime and making logistics smarter.

We are now looking for talented backend engineers who can help us expand and scale this vision. If you're passionate about working on meaningful challenges that blend engineering, data, and impact — this opportunity is for you.

### **Challenge Description**
In this coding challenge, you will build a **basic freight search management system**, a simplified version of one of the most important services powering FullTruck’s recommendation engine.

The purpose of the system is to enable carriers to register their **freight search preferences** — such as preferred lanes, acceptable price ranges, and other constraints — and to match these searches against available freights.

Your end goal is to implement the following endpoint:

`GET /freight/{freight_id}/find_matches/`

This endpoint, given a freight_id, should return the list of **freight searches** that **match the features of the target freight**. Matching criteria will be explained in the following section, but may involve comparisons of price ranges, origin and destination codes, and more.

You are **free to use any Python framework or ORM system you prefer**. However, to help you get started, we provide a **project template based on FastAPI and SQLAlchemy**, which you can use as a reference or base for your implementation.

You are **encouraged to design and implement all the necessary support endpoints** required to manage freight searches and freight records (e.g., create, list, etc.) so that the system is complete and testable from end to end.

Although your solution is not required to be tested against large-scale datasets, it should be **designed with scalability in mind**. The system should be able to support **millions of freight searches** efficiently, even if you're working with a much smaller dataset during development.

The focus of this challenge is on **clean architecture, scalability, and clarity** of the matching logic — not completeness of features.

### **Project Template Overview**
To help you focus on the core logic of the challenge, we provide a minimal FastAPI + SQLAlchemy template. You’re free to use any other Python backend framework or ORM system, but this project gives you a solid and pre-configured starting point with:
- A FastAPI server
- Async SQLAlchemy integration
- Example models and startup logic
- A utility script to run and test your endpoints programmatically
#### **Data Models**
```
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    surname = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)


class Freight(Base):
    __tablename__ = "freights"

    id = Column(Integer, primary_key=True, index=True)
    price = Column(Float, nullable=False)
    pickup_code = Column(Integer, index=True, nullable=False)
    delivery_code = Column(Integer, index=True, nullable=False)
    pickup_date = Column(Date, nullable=False)
    delivery_date = Column(Date, nullable=False)
```

- **User**: Represents a carrier or operator on the platform. In this challenge, each freight search will belong to a specific user, meaning users are essential for modeling ownership of search preferences.


- **Freight**: Represents a load to be matched. It includes a price, and two fields representing simplified geographical information:
  - pickup_code: A numeric code representing the origin area of the freight.
  - delivery_code: A numeric code representing the destination area.
  - pickup_date: The date the freight needs to be picked up.
  - delivery_date: The expected delivery date.

  These **geo codes** are abstractions of real-world locations (like zip codes or region codes) and are provided to **simplify the geographic aspect** of the project. You can treat them as identifiers for location-based filtering without needing complex spatial logic.
  
You will be expected to add a third model: FreightSearch, which stores user-defined preferences for future loads.

#### **Project Files**
Here’s an overview of the files provided in the template:
- **server.py
** The main FastAPI app definition. It contains a lifespan hook to initialize database tables and insert some sample data on startup.
- **models.py
** Where SQLAlchemy models are defined (User, Freight). You’ll add your custom models (like FreightSearch) here.
- **database.py
** Database setup: async engine configuration, session management, and a get_db dependency for FastAPI endpoints.
- **utils.py
** Utility functions, including api_call, which wraps async HTTP requests (useful when testing endpoints from within Python).
- **api_script.py
** A convenient **entry point script** to run the challenge project. It:
  - Starts the FastAPI server using uvicorn,
  - Waits for it to become ready,
  - Makes an example call (to /hello/),
  - Shuts down the server automatically. 
  
  This file is especially helpful to **facilitate development and testing** without needing to manually start and interact with the server each time.

### **FreightSearch and Matching Logic**
As part of the challenge, you will introduce a new model representing a **freight search**. A freight search captures the intent and preferences of a user (typically a carrier) regarding the types of freight they are interested in. This includes, but is not limited to:
- Preferred origin and destination areas
- Acceptable price ranges
- Pickup and delivery date windows

Each freight search must be **associated with a user**, representing the owner of that search.

The key goal of the system is to identify which of these freight searches are relevant to a given freight. This is the purpose of the endpoint:

`GET /freight/{freight_id}/find_matches/`

This endpoint should return a list of freight searches that match the characteristics of the target freight. The matching logic should compare attributes of the freight (such as price, route, and timing) with the conditions expressed in the freight search.

Importantly, **a freight search may specify all or some of the filtering conditions**. For example, one search may only constrain the origin and destination, while another may include specific date and price constraints.

You are free to define the fields and structure of the FreightSearch model, as long as it allows for a meaningful and scalable matching process. You are also encouraged to use indexes or filtering strategies that would allow this logic to scale to large volumes of data (1M+ freight searches), even if you're only working with a smaller sample in practice.

The response of the endpoint should return the matching freight searches in a clear and concise format.

### **Submission Guidelines**
You are expected to complete the challenge and submit your work **within 7 days** from the moment you receive it.

Please send your solution as a **zip file** containing all source code, and include:

- Clear instructions to set up and run the project locally
- Scripts/tests to clearly show the correctness of the implementation

Your submission will be evaluated based on:

- **Correctness** of implementation and completeness of the core logic
- **Code clarity** and maintainability
- **Scalability** and attention to performance under high data volume
- **API design** and adherence to good RESTful practices

If you have any questions or need clarification during the challenge, feel free to reach out to us.

We’re looking forward to seeing your solution — good luck!