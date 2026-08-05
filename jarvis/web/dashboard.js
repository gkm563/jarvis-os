/* JARVIS OS Web Dashboard Frontend Logic */

const API_BASE = window.location.origin;

let activePlanId = null;
let pollInterval = null;

document.addEventListener("DOMContentLoaded", () => {
    fetchHealth();
    fetchAgents();
    setInterval(fetchPendingApprovals, 2000);
});

// Submit Goal / Intent
async function submitGoal(customPrompt = null) {
    const inputEl = document.getElementById("goalInput");
    const goal = customPrompt || inputEl.value.trim();
    if (!goal) return;

    logMessage(`Submitting user goal: "${goal}"`, "info");
    inputEl.value = "";

    try {
        const response = await fetch(`${API_BASE}/v1/intent`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ user_goal: goal, execute_immediately: true })
        });

        if (!response.ok) throw new Error("Failed to process intent");

        const data = await response.json();
        activePlanId = data.plan_id;
        logMessage(`Plan created [${data.plan_id.substring(0, 8)}...] with ${data.step_count} steps. Starting execution...`, "success");

        renderPlan(data.plan);
        startPlanPolling(activePlanId);
    } catch (err) {
        logMessage(`Error submitting goal: ${err.message}`, "error");
    }
}

// Preset Execution Helper
function runPreset(prompt) {
    document.getElementById("goalInput").value = prompt;
    submitGoal(prompt);
}

// Render Plan DAG Steps
function renderPlan(plan) {
    const dagContainer = document.getElementById("dagContainer");
    dagContainer.innerHTML = "";

    if (!plan || !plan.steps || plan.steps.length === 0) {
        dagContainer.innerHTML = `<div class="step-meta">No active execution plan. Enter a goal above.</div>`;
        return;
    }

    plan.steps.forEach(step => {
        const stepEl = document.createElement("div");
        const statusClass = step.status ? step.status.toLowerCase() : "pending";
        stepEl.className = `dag-step ${statusClass}`;

        stepEl.innerHTML = `
            <div class="step-info">
                <div class="step-title">${step.description}</div>
                <div class="step-meta">Agent: <strong>${step.action.agent_name}</strong> | Action: <code>${step.action.action_type}</code></div>
            </div>
            <div class="badge badge-${statusClass}">${step.status}</div>
        `;
        dagContainer.appendChild(stepEl);
    });
}

// Poll Plan Execution Progress
function startPlanPolling(planId) {
    if (pollInterval) clearInterval(pollInterval);

    pollInterval = setInterval(async () => {
        try {
            const res = await fetch(`${API_BASE}/v1/plan/${planId}`);
            if (!res.ok) {
                clearInterval(pollInterval);
                return;
            }

            const plan = await res.json();
            renderPlan(plan);

            if (plan.status === "COMPLETED" || plan.status === "FAILED") {
                if (plan.status === "COMPLETED") {
                    logMessage(`Plan ${planId.substring(0, 8)} COMPLETED successfully!`, "success");
                } else {
                    logMessage(`Plan ${planId.substring(0, 8)} FAILED during execution.`, "error");
                }
                clearInterval(pollInterval);
            }
        } catch (err) {
            console.error("Polling error:", err);
            clearInterval(pollInterval);
        }
    }, 1000);
}

// Check Pending Approvals (Sensitive Action Gate)
async function fetchPendingApprovals() {
    try {
        const res = await fetch(`${API_BASE}/v1/pending_approvals`);
        if (!res.ok) return;

        const approvals = await res.json();
        const tokens = Object.keys(approvals);

        if (tokens.length > 0) {
            const token = tokens[0];
            const item = approvals[token];
            showApprovalModal(token, item);
        } else {
            hideApprovalModal();
        }
    } catch (err) {
        console.error("Error fetching approvals:", err);
    }
}

function showApprovalModal(token, details) {
    const modal = document.getElementById("approvalModal");
    document.getElementById("modalActionDesc").innerText = `${details.description} (${details.agent_name}:${details.action_type})`;
    document.getElementById("approveBtn").onclick = () => approveToken(token);
    modal.classList.add("active");
}

function hideApprovalModal() {
    document.getElementById("approvalModal").classList.remove("active");
}

async function approveToken(token) {
    try {
        logMessage(`Approving confirmation token ${token.substring(0, 8)}...`, "warn");
        const res = await fetch(`${API_BASE}/v1/plan/${activePlanId || 'any'}/confirm`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ confirmation_token: token })
        });
        if (res.ok) {
            logMessage(`Token approved successfully! Execution resuming...`, "success");
            hideApprovalModal();
        }
    } catch (err) {
        logMessage(`Failed to approve token: ${err.message}`, "error");
    }
}

// Fetch System Health
async function fetchHealth() {
    try {
        const res = await fetch(`${API_BASE}/health`);
        const data = await res.json();
        document.getElementById("healthStatus").innerText = `${data.app} v${data.version} Online`;
    } catch (e) {
        document.getElementById("healthStatus").innerText = "Connecting...";
    }
}

// Fetch Registered Domain Agents
async function fetchAgents() {
    try {
        const res = await fetch(`${API_BASE}/v1/agents`);
        const agents = await res.json();
        const grid = document.getElementById("agentsGrid");
        grid.innerHTML = "";

        agents.forEach(agent => {
            const el = document.createElement("div");
            el.className = "agent-item";
            el.innerHTML = `
                <div class="agent-icon">🤖</div>
                <div class="agent-name" title="${agent.description}">${agent.name}</div>
            `;
            grid.appendChild(el);
        });
    } catch (err) {
        console.error("Error fetching agents:", err);
    }
}

// Log Terminal Handler
function logMessage(msg, type = "info") {
    const term = document.getElementById("logTerminal");
    if (!term) return;
    const time = new Date().toLocaleTimeString();
    const entry = document.createElement("div");
    entry.className = `log-entry ${type}`;
    entry.innerText = `[${time}] ${msg}`;
    term.appendChild(entry);
    term.scrollTop = term.scrollHeight;
}
