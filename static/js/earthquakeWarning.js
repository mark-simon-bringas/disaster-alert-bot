async function loadPhivolcsWarning() {
    const container = document.getElementById("phivolcs-warning-container");

    // Initial loading state
    container.innerHTML = `
        <div class="alert-card alert-safe">
            <div class="d-flex align-items-start">
                <i class="bi bi-hourglass-split me-3 fs-4"></i>
                <div>
                    <h6 class="fw-bold mb-1">Fetching PHIVOLCS Earthquake Data...</h6>
                    <small class="text-muted">Please wait</small>
                </div>
            </div>
        </div>
    `;

    try {
        const res = await fetch("/earthquake_warning");
        const data = await res.json();

        // Handle API error
        if (data.error) {
            container.innerHTML = `
                <div class="alert-card alert-safe">
                    <div class="d-flex align-items-start">
                        <i class="bi bi-activity me-3 fs-4"></i>
                        <div>
                            <h6 class="fw-bold mb-1">No Significant Earthquake</h6>
                            <small class="text-muted">${data.error}</small>
                        </div>
                    </div>
                </div>
            `;
            return;
        }

        const eq = data.data;

        // Determine style (>= 6 = dangerous, >= 4 = warning, < 4 = safe)
        let alertClass = "alert-warning";
        try {
            const magValue = parseFloat(eq.magnitude.replace(/[^0-9.]/g, ""));
            if (magValue >= 6) alertClass = "alert-danger";
            else if (magValue < 4) alertClass = "alert-safe";
        } catch (e) {
            alertClass = "alert-warning";
        }

        const cardHTML = `
            <div class="alert-card ${alertClass}">
                <div class="d-flex align-items-start">
                    <i class="bi bi-exclamation-triangle-fill me-3 fs-3"></i>

                    <div style="flex-grow:1;">
                        <h6 class="fw-bold mb-1">
                            Earthquake • Magnitude ${eq.magnitude ?? "—"}
                        </h6>

                        <small class="text-muted">
                            <strong>Date:</strong> ${eq.date ?? "—"}<br>
                            <strong>Time:</strong> ${eq.time ?? "—"}<br>
                            <strong>Issued On:</strong> ${eq.issued_on ?? "—"}<br>

                            <strong>Location:</strong><br>
                            ${eq.location ?? "—"}<br>

                            <strong>Depth:</strong> ${eq.depth_of_focus ?? "—"}<br>
                            <strong>Aftershocks Expected:</strong> ${eq.aftershock ? "Yes" : "No"}<br>

                            <strong>Reported Intensities:</strong><br>
                            ${eq.reported_intensities_raw ?? "None"}<br>

                            <strong>Instrumental Intensities:</strong><br>
                            ${eq.instrumental_intensities_raw ?? "None"}
                        </small>
                    </div>
                </div>
            </div>
        `;

        container.innerHTML = cardHTML;

    } catch (err) {
        container.innerHTML = `
            <div class="alert-card alert-safe">
                <div class="d-flex align-items-start">
                    <i class="bi bi-x-circle me-3 fs-4"></i>
                    <div>
                        <h6 class="fw-bold mb-1">Failed to Load Earthquake Data</h6>
                        <small class="text-muted">${err.message}</small>
                    </div>
                </div>
            </div>
        `;
    }
}

document.addEventListener("DOMContentLoaded", loadPhivolcsWarning);
