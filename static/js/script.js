document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('estimateForm');
    const resultContainer = document.getElementById('resultContainer');
    const estimateResult = document.getElementById('estimateResult');

    form.addEventListener('submit', function(e) {
        e.preventDefault();
        const procedureCode = document.getElementById('procedureCode').value;
        const zipCode = document.getElementById('zipCode').value;

        fetch('/get_estimate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                procedure_code: procedureCode,
                zip_code: zipCode
            }),
        })
        .then(response => response.json())
        .then(data => {
            resultContainer.classList.remove('d-none');
            if (data.error) {
                estimateResult.innerHTML = `<p class="text-danger">Error: ${data.error}</p>`;
            } else {
                estimateResult.innerHTML = `
                    <div class="card">
                        <div class="card-body">
                            <h5 class="card-title">${data.procedure}</h5>
                            <p class="card-text"><strong>Estimated Cost Range:</strong> ${data.cost_range}</p>
                            <p class="card-text"><strong>Additional Information:</strong> ${data.additional_info}</p>
                        </div>
                    </div>
                `;
            }
        })
        .catch(error => {
            resultContainer.classList.remove('d-none');
            estimateResult.innerHTML = `<p class="text-danger">Error: ${error.message}</p>`;
        });
    });
});
