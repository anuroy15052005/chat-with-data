const form = document.querySelector("#question-form");
const question = document.querySelector("#question");
const count = document.querySelector("#question-count");
const button = document.querySelector("#ask-button");
const status = document.querySelector("#status");
const result = document.querySelector("#result");
const answerBlock = document.querySelector(".answer-block");
const answer = document.querySelector("#answer");
const tableWrap = document.querySelector("#table-wrap");
const sql = document.querySelector("#sql");
const promptChips = document.querySelectorAll(".prompt-chip");

question.addEventListener("input", () => {
	count.textContent = `${question.value.length} / 300`;
});

promptChips.forEach((chip) => {
	chip.addEventListener("click", () => {
		question.value = chip.dataset.question;
		question.dispatchEvent(new Event("input"));
		question.focus();
	});
});

form.addEventListener("submit", async (event) => {
	event.preventDefault();
	const text = question.value.trim();
	if (!text) return;

	button.disabled = true;
	button.textContent = "Thinking...";
	status.textContent = "Querying your sales data...";
	status.className = "status";
	result.hidden = true;

	try {
		const response = await fetch("/ask", {
			method: "POST",
			headers: { "Content-Type": "application/json" },
			body: JSON.stringify({ question: text })
		});
		const data = await response.json();
		if (!response.ok) throw new Error(data.error || "Something went wrong.");

		answer.textContent = data.answer || "";
		answerBlock.hidden = !data.answer;
		sql.textContent = data.sql;
		renderTable(data.columns, data.rows);
		result.hidden = false;
		status.textContent = "Done";
		status.className = "status success";
	} catch (error) {
		status.textContent = error.message;
		status.className = "status error";
	} finally {
		button.disabled = false;
		button.textContent = "Ask question";
	}
});

function renderTable(columns, rows) {
	if (!rows.length) {
		tableWrap.innerHTML = "<p class=\"empty\">No matching data found.</p>";
		return;
	}
	const table = document.createElement("table");
	const head = document.createElement("tr");
	columns.forEach((column) => {
		const cell = document.createElement("th");
		cell.textContent = column;
		head.appendChild(cell);
	});
	table.createTHead().appendChild(head);
	const body = table.createTBody();
	rows.forEach((row) => {
		const tableRow = body.insertRow();
		row.forEach((value) => {
			const cell = tableRow.insertCell();
			cell.textContent = value ?? "";
		});
	});
	tableWrap.replaceChildren(table);
}
