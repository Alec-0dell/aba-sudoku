Currently only configured for basic front-end use, including prolog and clingo-based solving.

To start:

Backend:
``` 
uvicorn backend.main:app --host 127.0.0.1 --port 8080
```

Frontend:
``` 
cd web-interface
npm install 
npm start
```

To test solvers
```
python scripts/test_solvers.py
```
```
Solver | Difficulty | Boards | Avg Time (ms) | Correct | Correct %
-------+------------+--------+---------------+---------+----------
prolog | Easy       | 10     | 194.786       | 10/10   | 100.0%   
prolog | Medium     | 10     | 238.271       | 10/10   | 100.0%   
prolog | Hard       | 10     | 245.460       | 10/10   | 100.0%   
prolog | Diabolical | 10     | 248.425       | 10/10   | 100.0%   
clingo | Easy       | 10     | 25.430        | 10/10   | 100.0%   
clingo | Medium     | 10     | 14.408        | 10/10   | 100.0%   
clingo | Hard       | 10     | 13.009        | 10/10   | 100.0%   
clingo | Diabolical | 10     | 12.058        | 10/10   | 100.0%   
```
