"""
QuantumGreen - Quantum Optimization Engine (Qiskit QAOA Simulator)
Formulates smart energy load shifting as a Quadratic Unconstrained Binary Optimization
(QUBO) / Ising Hamiltonian, constructs a parameterized QAOA quantum circuit,
and runs variational quantum simulation with classical benchmarking.
"""

import time
import math
import warnings
import numpy as np
from scipy.sparse import SparseEfficiencyWarning
warnings.filterwarnings("ignore", category=SparseEfficiencyWarning)
from scipy.optimize import minimize
from qiskit import QuantumCircuit
from qiskit.circuit.library import QAOAAnsatz
from qiskit.quantum_info import SparsePauliOp, Statevector

# Default problem instances representing campus energy scheduling scenarios
CAMPUS_APPLIANCES = [
    {"name": "Campus Borewell Pump System", "power_kw": 15.0, "category": "Water/Pumps", "flexibility": "High"},
    {"name": "Research Autoclaves & Sterilizers", "power_kw": 22.0, "category": "Laboratory", "flexibility": "Medium"},
    {"name": "Hostel Central Laundry Facility", "power_kw": 18.0, "category": "Appliances", "flexibility": "High"},
    {"name": "Campus EV Shuttle Charging Bank", "power_kw": 30.0, "category": "Transport", "flexibility": "Medium"},
    {"name": "Commercial Kitchen Dishwashers", "power_kw": 12.0, "category": "Dining", "flexibility": "High"}
]

def build_energy_qubo_hamiltonian(appliances, tariff_delta=5.0, peak_penalty_weight=0.08):
    """
    Formulates the energy scheduling problem into an Ising Hamiltonian:
    Decision variable x_i in {0, 1}:
      x_i = 1 -> Scheduled during Peak Tariff Window (High Cost + Grid Strain)
      x_i = 0 -> Scheduled during Valley / Off-Peak Window (Low Cost + Green Grid)

    Cost Function to Minimize:
      C(x) = sum_i (tariff_delta * P_i) * x_i + lambda * sum_{i < j} (P_i * P_j) * x_i * x_j

    Ising mapping: x_i = (I - Z_i) / 2
      x_i * x_j = (I - Z_i - Z_j + Z_i * Z_j) / 4
    """
    n_qubits = len(appliances)
    powers = np.array([app["power_kw"] for app in appliances])

    # Linear and Quadratic coefficients in QUBO:
    # Q_ii = tariff_delta * P_i
    # Q_ij = peak_penalty_weight * P_i * P_j  (for i < j)
    h_linear = np.zeros(n_qubits)
    J_quad = np.zeros((n_qubits, n_qubits))
    constant_offset = 0.0

    # Linear terms
    for i in range(n_qubits):
        c_i = tariff_delta * powers[i]
        # x_i = 0.5 * I - 0.5 * Z_i
        constant_offset += 0.5 * c_i
        h_linear[i] += -0.5 * c_i

    # Quadratic interaction terms (couplings)
    for i in range(n_qubits):
        for j in range(i + 1, n_qubits):
            w_ij = peak_penalty_weight * powers[i] * powers[j]
            # x_i * x_j = 0.25 * (I - Z_i - Z_j + Z_i * Z_j)
            constant_offset += 0.25 * w_ij
            h_linear[i] += -0.25 * w_ij
            h_linear[j] += -0.25 * w_ij
            J_quad[i, j] += 0.25 * w_ij

    # Build Pauli list for Qiskit SparsePauliOp
    pauli_list = []

    # ZZ interaction terms
    for i in range(n_qubits):
        for j in range(i + 1, n_qubits):
            val = J_quad[i, j]
            if abs(val) > 1e-6:
                # Qiskit qubit ordering: qubit 0 is rightmost in bitstring
                chars = ["I"] * n_qubits
                chars[n_qubits - 1 - i] = "Z"
                chars[n_qubits - 1 - j] = "Z"
                pauli_str = "".join(chars)
                pauli_list.append((pauli_str, float(val)))

    # Z single-qubit terms
    for i in range(n_qubits):
        val = h_linear[i]
        if abs(val) > 1e-6:
            chars = ["I"] * n_qubits
            chars[n_qubits - 1 - i] = "Z"
            pauli_str = "".join(chars)
            pauli_list.append((pauli_str, float(val)))

    if not pauli_list:
        pauli_list.append(("I" * n_qubits, 0.0))

    cost_op = SparsePauliOp.from_list(pauli_list)
    return cost_op, constant_offset, powers

def evaluate_classical_cost(bitstring, powers, tariff_delta=5.0, peak_penalty_weight=0.08):
    """
    Computes exact cost of a candidate scheduling bitstring.
    bitstring: e.g. "0100" (qubit 0 is rightmost in Qiskit standard, we normalize to index 0..N-1)
    """
    bits = [int(b) for b in bitstring]
    # In Qiskit, bitstring string has qubit N-1 at index 0, qubit 0 at index N-1.
    # We reverse so bits[i] corresponds to appliance i
    bits_aligned = list(reversed(bits))

    linear_cost = sum(tariff_delta * powers[i] * bits_aligned[i] for i in range(len(bits_aligned)))
    peak_coupled_cost = 0.0
    for i in range(len(bits_aligned)):
        for j in range(i + 1, len(bits_aligned)):
            peak_coupled_cost += peak_penalty_weight * powers[i] * powers[j] * bits_aligned[i] * bits_aligned[j]

    total_cost = linear_cost + peak_coupled_cost
    peak_kw = sum(powers[i] * bits_aligned[i] for i in range(len(bits_aligned)))
    offpeak_kw = sum(powers[i] * (1 - bits_aligned[i]) for i in range(len(bits_aligned)))

    return total_cost, peak_kw, offpeak_kw

def run_quantum_optimization(num_qubits=4, qaoa_reps=1, tariff_delta=5.0):
    """
    Executes a real Qiskit QAOA quantum simulation on the energy scheduling problem,
    compares against classical exact brute-force and classical greedy baseline.
    """
    start_total_time = time.perf_counter()

    # Select appliances for problem size (4 or 5 qubits)
    num_qubits = min(5, max(3, int(num_qubits)))
    selected_appliances = CAMPUS_APPLIANCES[:num_qubits]

    # 1. Build Problem Hamiltonian
    cost_op, offset, powers = build_energy_qubo_hamiltonian(
        selected_appliances,
        tariff_delta=tariff_delta,
        peak_penalty_weight=0.08
    )

    # 2. Classical Exact Benchmark (Exhaustive search over 2^N states)
    start_classical = time.perf_counter()
    all_states = [format(i, f"0{num_qubits}b") for i in range(2**num_qubits)]
    classical_results = []
    for state in all_states:
        cost, peak_kw, offpeak_kw = evaluate_classical_cost(state, powers, tariff_delta)
        classical_results.append({
            "bitstring": state,
            "cost": cost,
            "peak_kw": peak_kw,
            "offpeak_kw": offpeak_kw
        })
    classical_results.sort(key=lambda x: x["cost"])
    classical_best = classical_results[0]
    classical_runtime_ms = round((time.perf_counter() - start_classical) * 1000, 3)

    # Classical Greedy Solution (Schedule each appliance to valley if possible)
    start_greedy = time.perf_counter()
    greedy_bits = [0] * num_qubits # valley is 0
    greedy_state = "".join(str(b) for b in reversed(greedy_bits))
    greedy_cost, greedy_peak, greedy_offpeak = evaluate_classical_cost(greedy_state, powers, tariff_delta)
    greedy_runtime_ms = round((time.perf_counter() - start_greedy) * 1000, 3)

    # 3. Quantum QAOA Simulation using Qiskit
    start_quantum = time.perf_counter()
    qaoa = QAOAAnsatz(cost_operator=cost_op, reps=qaoa_reps)
    num_params = qaoa.num_parameters

    # Initial parameter guess: gamma in [0, pi], beta in [0, pi/2]
    init_params = np.array([0.4] * (num_params // 2) + [0.3] * (num_params // 2))

    # Objective function for classical optimizer (COBYLA)
    def qaoa_energy_objective(params):
        bound_circuit = qaoa.assign_parameters(params)
        sv = Statevector.from_instruction(bound_circuit)
        # Expectation value of cost Hamiltonian
        exp_energy = sv.expectation_value(cost_op).real + offset
        return exp_energy

    # Optimize QAOA angles using COBYLA
    opt_res = minimize(
        qaoa_energy_objective,
        init_params,
        method="COBYLA",
        options={"maxiter": 35, "tol": 1e-3}
    )

    # Extract final quantum statevector and measurement distribution
    best_qc = qaoa.assign_parameters(opt_res.x)
    final_sv = Statevector.from_instruction(best_qc)
    raw_probs = final_sv.probabilities_dict()

    quantum_runtime_ms = round((time.perf_counter() - start_quantum) * 1000, 3)

    # Format state probability distribution
    distribution = []
    for state in all_states:
        prob = float(raw_probs.get(state, 0.0))
        cost, peak_kw, offpeak_kw = evaluate_classical_cost(state, powers, tariff_delta)
        distribution.append({
            "bitstring": state,
            "probability": round(prob, 4),
            "percentage": round(prob * 100, 2),
            "cost": round(cost, 2),
            "is_classical_optimum": (state == classical_best["bitstring"])
        })

    # Sort distribution by probability descending
    distribution.sort(key=lambda x: x["probability"], reverse=True)
    quantum_best_measured = distribution[0]

    # Calculate Quantum Optimality Gap
    opt_gap_percent = 0.0
    if classical_best["cost"] > 0:
        opt_gap_percent = round(
            abs(quantum_best_measured["cost"] - classical_best["cost"]) / classical_best["cost"] * 100,
            2
        )

    # Probability of measuring the optimal solution
    optimal_state_prob = float(raw_probs.get(classical_best["bitstring"], 0.0))

    # Circuit decomposition details
    circuit_summary = {
        "num_qubits": num_qubits,
        "qaoa_layers_p": qaoa_reps,
        "total_parameters": num_params,
        "circuit_depth": best_qc.depth(),
        "total_gates": sum(best_qc.count_ops().values()),
        "cnot_entanglement_gates": best_qc.count_ops().get("cx", 0) + best_qc.count_ops().get("rzz", 0),
        "single_qubit_rotations": best_qc.count_ops().get("rx", 0) + best_qc.count_ops().get("rz", 0) + best_qc.count_ops().get("h", 0)
    }

    # Appliance schedule decoding for the quantum chosen state
    # Recall bitstring is reversed: bit at index i corresponds to appliances[i]
    quantum_bits = [int(b) for b in reversed(quantum_best_measured["bitstring"])]
    quantum_schedule_table = []
    for i, app in enumerate(selected_appliances):
        assigned_slot = "Peak Hours (18:00 - 22:00)" if quantum_bits[i] == 1 else "Valley / Off-Peak (00:00 - 06:00)"
        status_tag = "High Grid Stress" if quantum_bits[i] == 1 else "Optimized Green Slot"
        quantum_schedule_table.append({
            "equipment": app["name"],
            "category": app["category"],
            "power_kw": app["power_kw"],
            "bit_value": quantum_bits[i],
            "assigned_window": assigned_slot,
            "status_tag": status_tag
        })

    return {
        "status": "success",
        "algorithm": f"Qiskit QAOA Simulator (p={qaoa_reps})",
        "is_quantum_simulator": True,
        "problem_spec": {
            "num_qubits": num_qubits,
            "search_space_size": 2**num_qubits,
            "tariff_delta": tariff_delta,
            "appliances": selected_appliances
        },
        "quantum_solution": {
            "best_bitstring": quantum_best_measured["bitstring"],
            "measured_cost": round(quantum_best_measured["cost"], 2),
            "probability": round(quantum_best_measured["probability"], 4),
            "probability_percentage": round(quantum_best_measured["percentage"], 2),
            "optimal_state_hit_probability": round(optimal_state_prob * 100, 2),
            "runtime_ms": quantum_runtime_ms,
            "schedule": quantum_schedule_table
        },
        "classical_baseline": {
            "exact_bitstring": classical_best["bitstring"],
            "exact_cost": round(classical_best["cost"], 2),
            "runtime_ms": classical_runtime_ms,
            "greedy_bitstring": greedy_state,
            "greedy_cost": round(greedy_cost, 2),
            "greedy_runtime_ms": greedy_runtime_ms
        },
        "benchmark_comparison": {
            "optimality_gap_percent": opt_gap_percent,
            "is_optimal_found": (quantum_best_measured["bitstring"] == classical_best["bitstring"]),
            "quantum_runtime_ms": quantum_runtime_ms,
            "classical_runtime_ms": classical_runtime_ms,
            "speed_difference_note": (
                "For this small problem (N=4 qubits), classical exact search takes < 1 ms because 2^4 = 16 states. "
                "The quantum simulator simulates full statevectors on a classical CPU which takes ~30-50 ms. "
                "Quantum computing advantage is expected when N > 50 qubits where 2^N exceeds 10^15 states."
            )
        },
        "circuit_metrics": circuit_summary,
        "probability_distribution": distribution[:8], # Top 8 most probable quantum states
        "educational_notes": {
            "simulator_vs_hardware": (
                "This demonstration runs on Qiskit's high-fidelity Statevector Simulator. In physical quantum hardware "
                "(such as IBM Quantum Heron or Eagle processors), superconducting transmon qubits experience thermal decoherence (T1, T2) "
                "and two-qubit gate cross-talk, requiring Error Mitigation (e.g. Dynamical Decoupling or Twirled Readout Error Extinction)."
            ),
            "climate_impact": (
                "Combinatorial grid scheduling allows simultaneous coordination of thousands of distributed energy resources (DERs), "
                "curbing peaker plant reliance and reducing carbon emissions by up to 22% during regional peak strain."
            )
        }
    }
