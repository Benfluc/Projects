# **Logistics Cost Minimization**

## About the Problem:

A company needs to distribute its products to different destinations using distribution centers with limited capacity.
Each center has a unit shipping cost, and each destination has a specific demand.
The goal is to minimize the total transportation cost while respecting the supply available at each center and the demand at each destination.

The costs, as well as the relationship between supply and demand, are given in the table below:

Origin/Destination  |  D1  |  D2  |   D3  |
--------------------|------|------|-------|
CD1                 |  4   |   6  |   8   |
CD2                 |  2   |   4  |   5   |
CD3                 |  3   |   1  |   7   |

*Unit transportation costs (R$/unit)*

Solution:

The problem can be formulated by assigning a variable (X_ij) for each Distribution Center (DC) and Destination (D), establishing a direct relationship between i and j. By transforming these flows into Xij values, we have:

F.O.[min]: *4x11+ 6x12 + 8x13 + 2x21 + 4x22 + 5x23 + 3x31 + x32 + 7x33*

Subject to:

        Supply constraints:      
            x11 + x12 + x13 = 80
            x21 + x22 + x23 = 100
            x31 + x32 + x33 = 120
       
        Demand constraints:  
            x11 + x21 + x31 = 90
            x12 + x22 + x32 = 70
            x13 + x23 + x33 = 140


### Northwest Corner Method

The Northwest Corner Method is a simple technique used to find an initial solution to transportation problems, which involve distributing products from multiple origins to different destinations in order to minimize costs or meet demands.

The name “Northwest Corner” comes from the starting point of the method: it always begins at the upper-left cell (northwest corner) of the transportation table. From there, the maximum possible allocation is assigned to that cell, the corresponding supply and demand are adjusted, and then the process moves to the next cell to the right or below, repeating until all demands are met.

This method is feasible mainly for balanced transportation problems, where the sum of supplies equals the sum of demands. It is useful for quickly generating an initial solution, which can later be optimized using methods such as MODI (Modified Distribution Method) or Stepping Stone to find the minimum-cost solution. Although it does not guarantee the optimal solution, it is efficient for obtaining an initial feasible basis, especially in large problems where starting from scratch would be more complex.

Given the objective function described earlier, we can transform it into a matrix A.

**Code:**

### Creating the calculation function:
```python
# Importing the Numpy library
def northwest_corner(costs, supply, demand):
    # Generates initial solution using the northwest corner method.
    supply = supply.copy()
    demand = demand.copy()
    allocation = np.zeros_like(costs, dtype=int)
    
    i, j = 0, 0
    while i < 3 and j < 3:
        qty = min(supply[i], demand[j])
        allocation[i][j] = qty
        supply[i] -= qty
        demand[j] -= qty
        if supply[i] == 0 and demand[j] == 0:
            i += 1
            j += 1
        elif supply[i] == 0:
            i += 1
        else:
            j += 1
    return allocation
```
What the code does here is iterate through the allocation matrix starting at position (1,1) (row 1, column 1) and fill it with the minimum between supply and demand.
After that, the remaining supply or demand is updated, and the process moves to the next DC × D relation until all supplies and demands are satisfied.
In the end, we have a solution that meets the constraints, although it is not necessarily optimal.

### Searching for the optimal solution:
```python
def calculate_potentials(allocation, costs):
    # Calculates u,v potentials and reduced costs delta.
    u = [None]*3
    v = [None]*3
    u[0] = 0
    basic = [(i,j) for i in range(3) for j in range(3) if allocation[i][j] > 0]
    
    changed = True
    while changed:
        changed = False
        for i,j in basic:
            if u[i] is not None and v[j] is None:
                v[j] = costs[i][j] - u[i]
                changed = True
            elif v[j] is not None and u[i] is None:
                u[i] = costs[i][j] - v[j]
                changed = True
                
    delta = np.zeros_like(costs, dtype=int)
    for i in range(3):
        for j in range(3):
            if (i,j) not in basic:
                delta[i][j] = costs[i][j] - (u[i] + v[j])
    return u, v, delta
```
Here we begin the search for the optimal solution. Since this is a balanced problem (supply and demand both equal 300), the number of basic variables is given by *(m + n - 1)*.
Substituting: (3 + 3 - 1) = 5.
or each Delta(*Xij*), *Cij* - (*ui* + *vj*), where:

- *Cij* = Unit cost of cell *ij*;
- *ui* = Potential associated with row *DCi*;
- *vj* = Potential associated with column (Destination *j*)

The basic variables found in the previous method were: (1,1), (2,1), (2,2), (2,3), (3,3), and we assume *u1* = 0.

```python
def find_loop(allocation, start):
    # Finds closed loop in 3x3 for starting cell (i,j).
    i0,j0 = start
    basic = [(i,j) for i in range(3) for j in range(3) if allocation[i][j] > 0]
    basic.append((i0,j0))
    
    # For 3x3, we try alternating rows and columns
    # Generate simple possible combinations (like an L shape)
    for i1,j1 in basic:
        if i1 != i0 and j1 != j0 and (i1,j0) in basic and (i0,j1) in basic:
            return [(i0,j0),(i0,j1),(i1,j1),(i1,j0)]
    return None

def modi_3x3(costs, supply, demand):
    allocation = northwest_corner(costs, supply, demand)
    
    while True:
        u, v, delta = calculate_potentials(allocation, costs)
        if np.all(delta >= 0):
            break  # ótimo
        # select cell with minimum delta
        i,j = np.unravel_index(np.argmin(delta), delta.shape)
        loop = find_loop(allocation, (i,j))
        if loop is None:
            raise Exception("Não foi possível encontrar loop para melhoria")
        
        plus = loop[0::2]
        minus = loop[1::2]
        theta = min([allocation[x,y] for x,y in minus])
        
        for x,y in plus:
            allocation[x][y] += theta
        for x,y in minus:
            allocation[x][y] -= theta

    total_cost = np.sum(allocation * costs)
    u, v, delta = calculate_potentials(allocation, costs)
    return allocation, total_cost, u, v, delta
```

In the final part of the code, we create a function that finds the loop by alternating the substitution signs of the basic cell.
Initially, after calculating the reduced costs of the non-basic cells, we look for all *Cij* = 0 to obtain the optimal solution.
Values < 0 represent good gains in cost minimization and are added until the optimal solution is found, i.e., when all costs are equal to zero.

### Applying it to our real example:
```python
# Cost matrix
osts = np.array([
    [4, 6, 8],
    [2, 4, 5],
    [3, 1, 7]
])
supply = [80, 100, 120]
demand = [90, 70, 140]

alloc, cost, u, v, delta = modi_3x3(costs, supply, demand)

print("Optimal Matrix:\n", alloc)
print("Optimal Total Cost:", cost)
print("Potentials u:", u)
print("Potentials v:", v)
print("Reduced Costs (Delta):\n", delta)
```
Finally, we simply provide the cost matrix, built through the relationship between unit costs of distribution centers and destinations and the supply and demand constraints.
With this, we can call the created functions and obtain the optimal solution of the problem, as well as the optimal matrix and other information.

Saída:
 
      Optimal Matrix: [80, 0, 0], [0, 0, 100], [10, 70, 40]  
      Optimal Total Cost: 1200  
      Potentials u: [0, np.int64(-3), np.int64(-1)]  
      Potentials v: [np.int64(4), np.int64(2), np.int64(8)]  
      Reduced Costs (Delta): [0 4 0], [1 5 0], [0 0 0]  

### Final Considerations:

This code works for 3x3 matrices and assumes that there always exists a simple L-shaped loop for adjustment.
For larger matrices or more complex loops, a full loop detection algorithm would be required. However, these functions are still a good starting point for solving the problem and optimizing transportation.
If interested, the link below also provides a complete version with all calculations explained and a discussion on the feasibility of implementing this solution.
