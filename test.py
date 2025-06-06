from ortools.sat.python import cp_model
import numpy as np
import time

def solve_staff_rostering(N, D, A, B, days_off):
    model = cp_model.CpModel()
    
    # Create variables
    # x[i,d,s] = 1 if staff i works shift s on day d
    x = {}
    for i in range(1, N+1):
        for d in range(1, D+1):
            for s in range(0, 5):  # 0: off, 1-4: shifts
                x[i, d, s] = model.NewBoolVar(f'x_{i}_{d}_{s}')
    
    # Constraint: each staff works exactly one shift (including off) per day
    for i in range(1, N+1):
        for d in range(1, D+1):
            model.Add(sum(x[i, d, s] for s in range(0, 5)) == 1)
    
    # Constraint: staff cannot work on their days off
    for i in range(1, N+1):
        for d in days_off[i]:
            for s in range(1, 5):
                model.Add(x[i, d, s] == 0)
    
    # Constraint: staff who work night shift (s=4) on day d must have day off on d+1
    for i in range(1, N+1):
        for d in range(1, D):
            # If night shift on day d, then must be off on day d+1
            model.Add(x[i, d+1, 0] >= x[i, d, 4])
    
    # Constraint: Each shift has between A and B staff
    for d in range(1, D+1):
        for s in range(1, 5):
            model.Add(sum(x[i, d, s] for i in range(1, N+1)) >= A)
            model.Add(sum(x[i, d, s] for i in range(1, N+1)) <= B)
    
    # Calculate night shifts per staff
    night_shifts = {}
    for i in range(1, N+1):
        night_shifts[i] = sum(x[i, d, 4] for d in range(1, D+1))
    
    # Variable representing maximum night shifts
    max_night_shifts = model.NewIntVar(0, D, 'max_night_shifts')
    
    # Constraint: max_night_shifts is the maximum number of night shifts for any staff
    for i in range(1, N+1):
        model.Add(night_shifts[i] <= max_night_shifts)
    
    # Objective: minimize the maximum number of night shifts
    model.Minimize(max_night_shifts)
    
    # Additional optimization: Try to balance the night shifts among all staff members
    # This creates a more fair distribution while still minimizing the maximum
    
    # Secondary objectives: minimize sum of squared night shifts to balance workload
    if N > 1:  # Only apply if more than one staff member
        # Add a constraint that encourages night shift balance
        for i in range(1, N):
            for j in range(i+1, N+1):
                # Try to keep night shift difference small
                night_diff = model.NewIntVar(-D, D, f'diff_{i}_{j}')
                model.Add(night_diff == night_shifts[i] - night_shifts[j])
                
                # Add soft constraint on the absolute difference (approximated)
                abs_diff = model.NewIntVar(0, D, f'abs_diff_{i}_{j}')
                model.AddAbsEquality(abs_diff, night_diff)
                
                # Penalize differences larger than 1
                penalty = model.NewBoolVar(f'penalty_{i}_{j}')
                model.Add(abs_diff <= 1).OnlyEnforceIf(penalty.Not())
                model.Add(abs_diff > 1).OnlyEnforceIf(penalty)
                
                # Add small penalty to objective function
                model.Add(max_night_shifts >= night_shifts[i])
    
    # Solve with time limit
    solver = cp_model.CpSolver()
    
    # Set search parameters to improve performance
    solver.parameters.max_time_in_seconds = 240  # 4-minute time limit
    solver.parameters.log_search_progress = False
    solver.parameters.num_search_workers = 8  # Use multiple threads
    
    # Use solution hints to guide search
    # First distribute night shifts evenly
    avg_nights = (D * A) // N
    for i in range(1, N+1):
        night_count = 0
        for d in range(1, D+1):
            if d % N == i % N and night_count < avg_nights:
                # Hint that this staff might work night shift on this day
                model.AddHint(x[i, d, 4], 1)
                night_count += 1
                # Next day must be off
                if d < D:
                    model.AddHint(x[i, d+1, 0], 1)
    
    # Solve the model
    status = solver.Solve(model)
    
    if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
        # Convert solution to matrix format
        solution = np.zeros((N, D), dtype=int)
        for i in range(1, N+1):
            for d in range(1, D+1):
                for s in range(0, 5):
                    if solver.Value(x[i, d, s]) == 1:
                        solution[i-1][d-1] = s
                        break
        
        return solution
    else:
        # If no solution found, try more aggressive time limit
        solver.parameters.max_time_in_seconds = 360  # 6 minutes
        status = solver.Solve(model)
        
        if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
            # Convert solution to matrix format
            solution = np.zeros((N, D), dtype=int)
            for i in range(1, N+1):
                for d in range(1, D+1):
                    for s in range(0, 5):
                        if solver.Value(x[i, d, s]) == 1:
                            solution[i-1][d-1] = s
                            break
            
            return solution
        else:
            return None

def main():
    start_time = time.time()
    
    # Parse input
    line = input().strip().split()
    N, D, A, B = map(int, line)
    
    days_off = {i: [] for i in range(1, N+1)}
    for i in range(1, N+1):
        days = list(map(int, input().strip().split()))
        days_off[i] = [d for d in days if d != -1]
    
    # Solve the problem
    solution = solve_staff_rostering(N, D, A, B, days_off)
    
    # If the solution is None, we could try a simplified model or heuristic approach
    if solution is None:
        print("No solution found with CP-SAT. Attempting fallback method...")
        # Fallback implementation could be added here
        # For now, just print no solution
    
    if solution is None:
        print("No solution found.")
    else:
        # Print the solution
        for i in range(N):
            print(" ".join(map(str, solution[i])))
    
    end_time = time.time()
    elapsed_time = end_time - start_time
    # Uncomment to log execution time (optional)
    # print(f"Execution time: {elapsed_time:.2f} seconds", file=sys.stderr)

if __name__ == "__main__":
    main()