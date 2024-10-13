document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('estimateForm');
    const resultDiv = document.getElementById('result');
    const errorDiv = document.getElementById('error');
    const procedureSelect = document.getElementById('procedure');
    const otherProcedureDiv = document.getElementById('otherProcedureDiv');
    const otherProcedureInput = document.getElementById('otherProcedure');
    const loadingIndicator = document.createElement('div');
    loadingIndicator.className = 'spinner-border text-primary';
    loadingIndicator.setAttribute('role', 'status');
    loadingIndicator.innerHTML = '<span class="visually-hidden">Loading...</span>';

    procedureSelect.addEventListener('change', function() {
        if (this.value === 'Other') {
            otherProcedureDiv.style.display = 'block';
            otherProcedureInput.required = true;
        } else {
            otherProcedureDiv.style.display = 'none';
            otherProcedureInput.required = false;
        }
    });

    form.addEventListener('submit', function(e) {
        e.preventDefault();
        
        let procedure = procedureSelect.value;
        if (procedure === 'Other') {
            procedure = otherProcedureInput.value.trim();
        }
        const procedureCode = document.getElementById('procedureCode').value.trim();
        const zipCode = document.getElementById('zipCode').value.trim();

        if (!procedure || !zipCode) {
            displayError('Please fill in both the procedure and ZIP code fields.');
            return;
        }

        resultDiv.innerHTML = '';
        resultDiv.appendChild(loadingIndicator);
        errorDiv.innerHTML = '';

        fetch('/estimate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ procedure, zip_code: zipCode, procedure_code: procedureCode }),
        })
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            resultDiv.removeChild(loadingIndicator);
            if (data.error) {
                displayError(`Error: ${data.error}`);
            } else {
                displayEstimate(data);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            resultDiv.removeChild(loadingIndicator);
            displayError('An unexpected error occurred. Please try again later.');
        });
    });

    function displayError(message) {
        errorDiv.innerHTML = `<div class="alert alert-danger" role="alert">${message}</div>`;
        resultDiv.innerHTML = '';
    }

    function formatNumber(num) {
        return num !== null ? '$' + num.toFixed(2).replace(/\B(?=(\d{3})+(?!\d))/g, ",") : 'N/A';
    }

    function createCollapsibleSection(title, content) {
        const id = title.toLowerCase().replace(/\s+/g, '-');
        return `
            <div class="card mb-3">
                <div class="card-header" id="heading-${id}">
                    <h5 class="mb-0">
                        <button class="btn btn-link" type="button" data-bs-toggle="collapse" data-bs-target="#collapse-${id}" aria-expanded="false" aria-controls="collapse-${id}">
                            ${title}
                        </button>
                    </h5>
                </div>
                <div id="collapse-${id}" class="collapse" aria-labelledby="heading-${id}">
                    <div class="card-body">
                        ${content}
                    </div>
                </div>
            </div>
        `;
    }

    function displayEstimate(data) {
        const mainEstimateHtml = `
            <h2 class="mb-3">Cost Estimate</h2>
            <dl class="row">
                <dt class="col-sm-4">Procedure Name:</dt>
                <dd class="col-sm-8">${data.procedure_name || 'N/A'}</dd>
                
                <dt class="col-sm-4">Procedure Code:</dt>
                <dd class="col-sm-8">${data.procedure_code || 'N/A'}</dd>
                
                <dt class="col-sm-4">ZIP Code:</dt>
                <dd class="col-sm-8">${data.zip_code || 'N/A'}</dd>
                
                <dt class="col-sm-4">Estimated Cost Range:</dt>
                <dd class="col-sm-8">${formatNumber(data.low_estimate)} - ${formatNumber(data.high_estimate)}</dd>
                
                <dt class="col-sm-4">Typical Insurance Cost:</dt>
                <dd class="col-sm-8">${formatNumber(data.typical_insurance_cost)}</dd>
            </dl>
        `;

        const complicationsHtml = data.common_complications && data.common_complications.length > 0 ?
            `<ul>${data.common_complications.map(comp => `<li>${comp.name}: ${formatNumber(comp.estimated_cost)}</li>`).join('')}</ul>` :
            '<p>No common complications data available.</p>';

        const alternativeProceduresHtml = data.alternative_procedures && data.alternative_procedures.length > 0 ?
            `<ul>${data.alternative_procedures.map(alt => `<li>${alt.name}: ${formatNumber(alt.estimated_cost_range[0])} - ${formatNumber(alt.estimated_cost_range[1])}</li>`).join('')}</ul>` :
            '<p>No alternative procedures data available.</p>';

        const recoveryInfoHtml = data.recovery_info ?
            `<p>Estimated recovery time: ${data.recovery_info.estimated_time || 'N/A'}</p>
             <p>Associated costs: ${formatNumber(data.recovery_info.associated_costs)}</p>` :
            '<p>No recovery information available.</p>';

        const additionalInfoHtml = data.additional_info ?
            `<p>${data.additional_info}</p>` :
            '<p>No additional information available.</p>';

        const fullEstimateHtml = `
            ${mainEstimateHtml}
            ${createCollapsibleSection('Common Complications', complicationsHtml)}
            ${createCollapsibleSection('Alternative Procedures', alternativeProceduresHtml)}
            ${createCollapsibleSection('Recovery Information', recoveryInfoHtml)}
            ${createCollapsibleSection('Additional Information', additionalInfoHtml)}
        `;

        resultDiv.innerHTML = fullEstimateHtml;
        resultDiv.style.opacity = 0;
        resultDiv.style.transition = 'opacity 0.5s ease-in-out';
        setTimeout(() => {
            resultDiv.style.opacity = 1;
        }, 50);
    }
});
