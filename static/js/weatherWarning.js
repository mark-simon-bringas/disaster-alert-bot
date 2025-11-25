async function loadPagasaWarning() {
    const container = document.getElementById("pagasa-warning-container");

    container.innerHTML = `
        <div class="alert-card alert-safe">
            <div class="d-flex align-items-start">
                <i class="bi bi-hourglass-split me-3 fs-4"></i>
                <div>
                    <h6 class="fw-bold mb-1">Fetching PAGASA Bulletin...</h6>
                    <small class="text-muted">Please wait</small>
                </div>
            </div>
        </div>
    `;

    try {
        const res = await fetch("/weather_warning");
        const data = await res.json();

        if (data.error) {
            container.innerHTML = `
                <div class="alert-card alert-safe">
                    <div class="d-flex align-items-start">
                        <i class="bi bi-cloud me-3 fs-4"></i>
                        <div>
                            <h6 class="fw-bold mb-1">No Active Typhoon</h6>
                            <small class="text-muted">${data.error}</small>
                        </div>
                    </div>
                </div>
            `;
            return;
        }

        // Determine severity style
        let alertClass = "alert-warning";
        if (data.highest_tcws.signal_no >= 4) alertClass = "alert-danger";
        if (data.highest_tcws.signal_no === null) alertClass = "alert-safe";

        const cardHTML = `
            <div class="alert-card ${alertClass}">
                <div class="d-flex align-items-start">
                    <i class="bi bi-exclamation-triangle-fill me-3 fs-3"></i>

                    <div style="flex-grow:1;">
                        <h6 class="fw-bold mb-1">
                            ${data.classification ?? "—"} ${data.name ?? ""}
                        </h6>

                        <small class="text-muted">
                            <strong>As of:</strong> ${data.location.as_of ?? "N/A"}<br>
                            <strong>Location:</strong> ${data.location.description ?? "—"}<br>

                            <strong>Intensity</strong><br>
                            • Max Winds: ${data.intensity.max_winds_kmh ?? "—"} km/h<br>
                            • Gustiness: ${data.intensity.gustiness_kmh ?? "—"} km/h<br>
                            • Pressure: ${data.intensity.pressure_hpa ?? "—"} hPa<br>

                            <strong>Movement</strong><br>
                            • Direction: ${data.present_movement.direction ?? "—"}<br>
                            • Speed: ${data.present_movement.speed_kmh ?? "—"} km/h<br>

                            <strong>Highest TCWS:</strong><br>
                            Signal ${data.highest_tcws.signal_no ?? "—"}<br>
                            Areas: ${data.highest_tcws.affected_areas ?? "—"}
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
                        <h6 class="fw-bold mb-1">Failed to Load PAGASA Bulletin</h6>
                        <small class="text-muted">${err.message}</small>
                    </div>
                </div>
            </div>
        `;
    }
}

document.addEventListener("DOMContentLoaded", loadPagasaWarning);