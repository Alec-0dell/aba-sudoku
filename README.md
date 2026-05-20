Currently only configured for basic front-end use and prolog-based solving.

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

To test prolog solver
```
python scripts/test_solvers.py
```
```
Solver | Difficulty | Boards | Avg Time (ms) | Correct | Correct %
-------+------------+--------+---------------+---------+----------
prolog | Easy       | 100    | 24.162        | 100/100 | 100.0%   
prolog | Medium     | 100    | 25.242        | 100/100 | 100.0%   
prolog | Hard       | 100    | 27.221        | 100/100 | 100.0%   
prolog | Diabolical | 100    | 28.543        | 100/100 | 100.0%   
```