# Knowledge Capture & Decision History

This document logs key design decisions, trade-offs, and future plans, based on the current state of the codebase.

## 1. Key Design Decisions

*   **Microservices-based Architecture:** The application is divided into several services (frontend, backend, ml-worker), which allows for independent development, deployment, and scaling.
*   **Containerization:** The use of Docker and Docker Compose ensures a consistent and reproducible environment for all services.
*   **Asynchronous ML Processing:** The use of Celery for ML tasks ensures that the main API remains responsive, even when processing a large number of transactions.

## 2. Trade-offs

*   **Complexity:** A microservices-based architecture can be more complex to manage than a monolithic application.
*   **Development Overhead:** The use of multiple services and technologies can increase the development overhead.

## 3. Known Limitations

*   **Scalability:** While the architecture is designed to be scalable, the current implementation may have limitations that need to be addressed in the future.
*   **Security:** The security of the application can always be improved. Further security audits and penetration testing should be conducted.

## 4. Planned Improvements

*   **Enhanced Analytics:** Implement more advanced analytics and data visualization features.
*   **Mobile App:** Develop a native mobile app for iOS and Android.
*   **Investment Tracking:** Add support for tracking investments and retirement accounts.