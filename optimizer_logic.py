
from ortools.sat.python import cp_model
import time

class PlateOptimizationCallback(cp_model.CpSolverSolutionCallback):
    def __init__(self, tag_to_plate, ups_vars, plate_sheets, tags, plate_count, ups_per_plate, verbose=False):
        super().__init__()
        self.best_solution = None
        self.best_obj = float('inf')
        self.tag_to_plate = tag_to_plate
        self.ups_vars = ups_vars
        self.plate_sheets = plate_sheets
        self.tags = tags
        self.plate_count = plate_count
        self.ups_per_plate = ups_per_plate
        self.verbose = verbose
        self.solution_count = 0
        
        # Track improvement timing for early stopping (only for large datasets > 100)
        self.use_improvement_stopping = len(tags) > 100
        if self.use_improvement_stopping:
            self.last_improvement_time = time.time()
            self.improvement_timeout = 600  # 10 minutes in seconds
            self.start_time = time.time()

    def on_solution_callback(self):
        self.solution_count += 1
        obj = sum(self.Value(s) for s in self.plate_sheets)

        if obj < self.best_obj:
            self.best_obj = obj
            if self.use_improvement_stopping:
                self.last_improvement_time = time.time()  # Reset improvement timer
            results = []
            totalProduced = 0
            totalItems = sum(tag['QTY'] for tag in self.tags)

            for j in range(self.plate_count):
                for i in range(len(self.tags)):
                    if self.Value(self.tag_to_plate[i]) == j:
                        ups = self.Value(self.ups_vars[i])
                        sheets = self.Value(self.plate_sheets[j])
                        produced = ups * sheets
                        item = self.tags[i]

                        result = {
                            "COLOR": item["COLOR"],
                            "SIZE": item["SIZE"],
                            "QTY": item["QTY"],
                            "PLATE": chr(65 + j),
                            "OPTIMAL_UPS": ups,
                            "SHEETS_NEEDED": sheets,
                            "QTY_PRODUCED": produced,
                            "EXCESS": produced - item["QTY"]
                        }

                        # Add optional CEO fields if they exist
                        for field in ["ITEM_DESCRIPTION", "ITEM_CODE", "PRICE", "EP_NO", "RUN", "SHEET"]:
                            if field in item:
                                result[field] = item[field]

                        results.append(result)
                        totalProduced += produced

            totalSheets = sum(self.Value(s) for s in self.plate_sheets)
            totalExcess = totalProduced - totalItems
            waste = round((totalExcess / totalProduced) * 100, 2) if totalProduced else 0.0

            self.best_solution = {
                "results": results,
                "summary": {
                    "totalSheets": totalSheets,
                    "totalProduced": totalProduced,
                    "totalExcess": totalExcess,
                    "wastePercentage": waste,
                    "totalPlates": self.plate_count,
                    "totalItems": totalItems,
                    "upsCapacity": self.ups_per_plate,
                }
            }

            if self.verbose:
                if self.use_improvement_stopping:
                    elapsed_time = time.time() - self.start_time
                    print(f"\n🟢 New Best Solution Found!")
                    print(f"   ➤ Total Sheets: {totalSheets}")
                    print(f"   ➤ Waste %     : {waste}%")
                    print(f"   ➤ Excess Qty  : {totalExcess}")
                    print(f"   ➤ Produced    : {totalProduced}")
                    print(f"   ➤ Solution #{self.solution_count}")
                    print(f"   ➤ Time Elapsed: {elapsed_time:.1f}s\n")
                else:
                    print(f"\n🟢 New Best Solution Found!")
                    print(f"   ➤ Total Sheets: {totalSheets}")
                    print(f"   ➤ Waste %     : {waste}%")
                    print(f"   ➤ Excess Qty  : {totalExcess}")
                    print(f"   ➤ Produced    : {totalProduced}")
                    print(f"   ➤ Solution #{self.solution_count}\n")
        
        # Check if we should stop due to no improvement (only for large datasets > 100)
        if self.use_improvement_stopping:
            current_time = time.time()
            time_since_improvement = current_time - self.last_improvement_time
            
            if time_since_improvement >= self.improvement_timeout:
                if self.verbose:
                    total_elapsed = current_time - self.start_time
                    print(f"\n🛑 Stopping solver: No improvement for {self.improvement_timeout/60:.1f} minutes")
                    print(f"   ➤ Total runtime: {total_elapsed/60:.1f} minutes")
                    print(f"   ➤ Solutions found: {self.solution_count}")
                    print(f"   ➤ Best objective: {self.best_obj}\n")
                
                self.StopSearch()

def assign_ups_proportional(group, ups_per_plate):
    total_qty = sum(item['QTY'] for item in group)
    raw_ups = [
        max(1, round((item['QTY'] / total_qty) * ups_per_plate)) for item in group
    ]

    # Balance ups to make sure they sum exactly to ups_per_plate
    while sum(raw_ups) < ups_per_plate:
        min_index = raw_ups.index(min(raw_ups))
        raw_ups[min_index] += 1
    while sum(raw_ups) > ups_per_plate:
        max_index = raw_ups.index(max(raw_ups))
        if raw_ups[max_index] > 1:
            raw_ups[max_index] -= 1
        else:
            break

    return raw_ups

def initial_balanced_partition_no_singles(tags, plate_count):
    """Enhanced partitioning that avoids single-tag plates"""
    plates = [[] for _ in range(plate_count)]
    plate_loads = [0] * plate_count
    sorted_tags = sorted(tags, key=lambda t: t['QTY'], reverse=True)

    # First pass: distribute tags normally
    for tag in sorted_tags:
        min_index = plate_loads.index(min(plate_loads))
        plates[min_index].append(tag)
        plate_loads[min_index] += tag['QTY']

    # Second pass: fix single-tag plates by redistributing
    for i in range(len(plates)):
        if len(plates[i]) == 1:  # Single tag plate found
            single_tag = plates[i][0]
            plates[i] = []  # Clear this plate
            plate_loads[i] = 0
            
            # Find the plate with minimum load to add this tag
            min_index = plate_loads.index(min(plate_loads))
            plates[min_index].append(single_tag)
            plate_loads[min_index] += single_tag['QTY']

    return plates

def greedy_initialize(tags, ups_per_plate, plate_count):
    # Use enhanced partitioning for large datasets
    if len(tags) > 100:
        partitions = initial_balanced_partition_no_singles(tags, plate_count)
    else:
        partitions = initial_balanced_partition(tags, plate_count)
    
    initial_assignment = []

    for plate_index, group in enumerate(partitions):
        if group:  # Only process non-empty plates
            ups_list = assign_ups_proportional(group, ups_per_plate)
            for tag, ups in zip(group, ups_list):
                initial_assignment.append((tag, plate_index, ups))

    return initial_assignment

def initial_balanced_partition(tags, plate_count):
    plates = [[] for _ in range(plate_count)]
    plate_loads = [0] * plate_count
    sorted_tags = sorted(tags, key=lambda t: t['QTY'], reverse=True)

    for tag in sorted_tags:
        min_index = plate_loads.index(min(plate_loads))
        plates[min_index].append(tag)
        plate_loads[min_index] += tag['QTY']

    return plates

def solve_plate_optimization(tags, ups_per_plate, plate_count, seed_solution, verbose=False):
    model = cp_model.CpModel()
    num_tags = len(tags)
    all_plates = range(plate_count)
    enforce_min_tags = len(tags) > 100

    tag_to_plate = [model.NewIntVar(0, plate_count - 1, f'tag_{i}_plate') for i in range(num_tags)]
    ups_vars = [model.NewIntVar(1, ups_per_plate, f'ups_{i}') for i in range(num_tags)]
    plate_sheets = [model.NewIntVar(1, 10000, f'plate_sheet_{j}') for j in all_plates]
    
    # Apply greedy hints if available
    if seed_solution:
        for i, (tag, plate_index, ups) in enumerate(seed_solution):
            model.AddHint(tag_to_plate[i], plate_index)
            model.AddHint(ups_vars[i], ups)
            
    # Track which plates are actually used
    plate_used = [model.NewBoolVar(f'plate_used_{j}') for j in all_plates]
    tag_on_plate = [[model.NewBoolVar(f'tag_{i}_on_plate_{j}') for j in all_plates] for i in range(num_tags)]

    for j in all_plates:
        used_bools = []
        for i in range(num_tags):
            model.Add(tag_to_plate[i] == j).OnlyEnforceIf(tag_on_plate[i][j])
            model.Add(tag_to_plate[i] != j).OnlyEnforceIf(tag_on_plate[i][j].Not())
            used_bools.append(tag_on_plate[i][j])

            product_var = model.NewIntVar(1, 1000000, f'prod_tag_{i}_plate_{j}')
            model.AddMultiplicationEquality(product_var, [plate_sheets[j], ups_vars[i]])
            model.Add(product_var >= tags[i]['QTY']).OnlyEnforceIf(tag_on_plate[i][j])
            
        # Enforce that if any tag is assigned to plate j, the plate is used
        model.AddBoolOr(used_bools).OnlyEnforceIf(plate_used[j])
        model.AddBoolAnd([ub.Not() for ub in used_bools]).OnlyEnforceIf(plate_used[j].Not())
        
    for j in all_plates:
        ups_sum = []
        for i in range(num_tags):
            term = model.NewIntVar(0, ups_per_plate, f'active_ups_{i}_{j}')
            model.AddMultiplicationEquality(term, [ups_vars[i], tag_on_plate[i][j]])
            ups_sum.append(term)
            
        total_ups_on_plate = model.NewIntVar(0, ups_per_plate, f'total_ups_plate_{j}')
        model.Add(total_ups_on_plate == sum(ups_sum))
        
        model.Add(total_ups_on_plate == ups_per_plate).OnlyEnforceIf(plate_used[j])
        model.Add(total_ups_on_plate == 0).OnlyEnforceIf(plate_used[j].Not())
        
        # **CRITICAL FIX**: ABSOLUTELY PREVENT SINGLE TAG PLATES FOR LARGE DATASETS
        if enforce_min_tags:
            tag_count = model.NewIntVar(0, num_tags, f'tag_count_plate_{j}')
            model.Add(tag_count == sum(tag_on_plate[i][j] for i in range(num_tags)))
            
            # HARD CONSTRAINT: If plate is used, it MUST have at least 2 tags
            model.Add(tag_count >= 2).OnlyEnforceIf(plate_used[j])
            
            # Additional constraint: If tag_count == 1, then plate cannot be used
            single_tag_indicator = model.NewBoolVar(f'single_tag_indicator_{j}')
            model.Add(tag_count == 1).OnlyEnforceIf(single_tag_indicator)
            model.Add(tag_count != 1).OnlyEnforceIf(single_tag_indicator.Not())
            
            # If single tag indicator is true, plate CANNOT be used
            model.AddImplication(single_tag_indicator, plate_used[j].Not())
            
        else:
            # For smaller datasets, keep the old logic but make it work properly
            tag_count = model.NewIntVar(0, num_tags, f'tag_count_plate_{j}')
            model.Add(tag_count == sum(tag_on_plate[i][j] for i in range(num_tags)))

            only_one_tag = model.NewBoolVar(f'only_one_tag_plate_{j}')
            model.Add(tag_count == 1).OnlyEnforceIf(only_one_tag)
            model.Add(tag_count != 1).OnlyEnforceIf(only_one_tag.Not())

            under_utilized = model.NewBoolVar(f'under_utilized_plate_{j}')
            model.Add(total_ups_on_plate == ups_per_plate).OnlyEnforceIf(under_utilized)
            model.Add(total_ups_on_plate != ups_per_plate).OnlyEnforceIf(under_utilized.Not())

            forbidden_combo = model.NewBoolVar(f'forbidden_combo_{j}')
            model.AddBoolAnd([only_one_tag, under_utilized]).OnlyEnforceIf(forbidden_combo)
            model.Add(forbidden_combo == 0)  # Forbid it

    model.Minimize(sum(plate_sheets))

    solver = cp_model.CpSolver()
    
    # Time constraints based on dataset size
    if len(tags) > 100:
        # For large datasets > 100: No time limit, use improvement-based stopping
        if verbose:
            print(f"\n🚀 Starting optimization for {len(tags)} tags (Large Dataset)...")
            print(f"   ➤ Will stop if no improvement for 10 minutes")
    elif len(tags) > 50:
        solver.parameters.max_time_in_seconds = 600  # 10 minutes
        if verbose:
            print(f"\n🚀 Starting optimization for {len(tags)} tags...")
            print(f"   ➤ Time limit: 10 minutes")
    elif len(tags) > 25:
        solver.parameters.max_time_in_seconds = 300  # 5 minutes
        if verbose:
            print(f"\n🚀 Starting optimization for {len(tags)} tags...")
            print(f"   ➤ Time limit: 5 minutes")
    else:
        solver.parameters.max_time_in_seconds = 60
        if verbose:
            print(f"\n🚀 Starting optimization for {len(tags)} tags...")
            print(f"   ➤ Time limit: 2 minutes")
        
    solver.parameters.random_seed = 42
    solver.parameters.num_search_workers = 8

    cb = PlateOptimizationCallback(tag_to_plate, ups_vars, plate_sheets, tags, plate_count, ups_per_plate, verbose=verbose)
    status = solver.SolveWithSolutionCallback(model, cb)

    print(f"Solver status: {solver.StatusName(status)}")
    print(f"Total solutions tried: {cb.solution_count}")
    print(f"Wall time: {solver.WallTime():.2f}s")
    print(f"Best objective bound: {solver.BestObjectiveBound()}")
    print(f"Best found objective: {cb.best_obj}")

    if cb.best_solution:
        # Validate the solution to ensure no single-tag plates for large datasets
        if enforce_min_tags:
            plate_tag_counts = {}
            for result in cb.best_solution["results"]:
                plate = result["PLATE"]
                if plate not in plate_tag_counts:
                    plate_tag_counts[plate] = 0
                plate_tag_counts[plate] += 1
            
            single_tag_plates = [plate for plate, count in plate_tag_counts.items() if count == 1]
            if single_tag_plates:
                print(f"⚠️ WARNING: Found single-tag plates: {single_tag_plates}")
                print("This should not happen with the new constraints!")
            else:
                print("✅ SUCCESS: No single-tag plates found!")
        
        return cb.best_solution

    print("⚠️ No solution was found!")
    return {"error": "No solution found"}