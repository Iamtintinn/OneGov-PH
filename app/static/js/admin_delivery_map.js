(function () {
    var configs = window.ONE_GOV_ADMIN_DELIVERY_MAPS || [];
    if (!window.L || !configs.length) { return; }
    var configById = {};
    configs.forEach(function (config) { configById[config.map_id] = config; });

    function pointOnRoute(route, progress) {
        var segments = [];
        var total = 0;
        for (var index = 1; index < route.length; index += 1) {
            var start = route[index - 1];
            var end = route[index];
            var length = Math.hypot(end[0] - start[0], end[1] - start[1]);
            segments.push({ start: start, end: end, length: length });
            total += length;
        }
        var target = Math.max(0, Math.min(progress, 1)) * total;
        for (var segmentIndex = 0; segmentIndex < segments.length; segmentIndex += 1) {
            var segment = segments[segmentIndex];
            if (target <= segment.length || segmentIndex === segments.length - 1) {
                var ratio = segment.length ? target / segment.length : 0;
                return [
                    segment.start[0] + (segment.end[0] - segment.start[0]) * ratio,
                    segment.start[1] + (segment.end[1] - segment.start[1]) * ratio
                ];
            }
            target -= segment.length;
        }
        return route[route.length - 1];
    }

    function vehicleIcon() {
        return L.divIcon({
            className: "admin-track-vehicle-icon",
            html: '<span class="admin-track-vehicle"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3 7h10v8H3z"></path><path d="M13 10h4l3 3v2h-7z"></path><circle cx="7" cy="17" r="2"></circle><circle cx="17" cy="17" r="2"></circle></svg></span>',
            iconSize: [38, 38],
            iconAnchor: [19, 19]
        });
    }

    function buildMap(element, config) {
        var map = L.map(element, { scrollWheelZoom: false, zoomControl: true });
        L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
            maxZoom: 19,
            attribution: "&copy; OpenStreetMap contributors"
        }).addTo(map);
        var start = [config.start.lat, config.start.lng];
        var destination = [config.destination.lat, config.destination.lng];
        var route = (config.route || [start, destination]).map(function (point) {
            return [Number(point[0]), Number(point[1])];
        });
        var line = L.polyline(route, { color: "#3B82B0", weight: 5, opacity: 0.8 }).addTo(map);
        L.circleMarker(start, { radius: 8, color: "#245878", fillColor: "#245878", fillOpacity: 1 })
            .addTo(map).bindPopup("<strong>Starting point</strong><br>" + config.start.label);
        L.circleMarker(destination, { radius: 8, color: "#781F3A", fillColor: "#781F3A", fillOpacity: 1 })
            .addTo(map).bindPopup("<strong>Delivery destination</strong><br>" + config.destination.label);
        var marker = L.marker(route[0], { icon: vehicleIcon(), title: "Simulated delivery vehicle" }).addTo(map);
        map.fitBounds(line.getBounds(), { padding: [36, 36] });
        element._adminDelivery = {
            map: map,
            marker: marker,
            line: line,
            route: route,
            progress: Number(config.progress || 0),
            fromProgress: Number(config.from_progress != null ? config.from_progress : 0),
            frame: null,
            routeRequestId: 0
        };
        return element._adminDelivery;
    }

    function loadRoute(state, config) {
        var routeUrl = window.ONE_GOV_ROUTE_URL;
        if (!routeUrl || !config.start || !config.destination || !window.fetch) { return; }
        state.routeRequestId += 1;
        var requestId = state.routeRequestId;
        var query = new URLSearchParams({
            start_lat: String(config.start.lat),
            start_lng: String(config.start.lng),
            end_lat: String(config.destination.lat),
            end_lng: String(config.destination.lng)
        });
        fetch(routeUrl + "?" + query.toString(), { credentials: "same-origin" })
            .then(function (response) {
                if (!response.ok) { throw new Error("route unavailable"); }
                return response.json();
            })
            .then(function (data) {
                if (requestId !== state.routeRequestId) { return; }
                var coordinates = Array.isArray(data.coordinates) ? data.coordinates : [];
                if (coordinates.length < 2) { return; }
                state.route = coordinates.map(function (point) {
                    return [Number(point[0]), Number(point[1])];
                });
                state.line.setLatLngs(state.route);
                state.map.fitBounds(state.line.getBounds(), { padding: [36, 36] });
                state.marker.setLatLng(pointOnRoute(state.route, state.progress));
            })
            .catch(function () {});
    }

    function animateDelivery(element, state) {
        if (state.frame) { cancelAnimationFrame(state.frame); }
        var startedAt = performance.now();
        var duration = 1800;
        var targetProgress = state.progress;
        var startProgress = state.fromProgress;
        if (startProgress > targetProgress) { startProgress = 0; }
        var panel = element.closest(".admin-track-map-panel");
        var progressBar = panel ? panel.querySelector(".admin-track-progress span") : null;
        var progressText = panel ? panel.querySelector("[data-delivery-progress]") : null;
        function frame(now) {
            var elapsed = Math.min((now - startedAt) / duration, 1);
            var progress = startProgress + (targetProgress - startProgress) * elapsed;
            state.marker.setLatLng(pointOnRoute(state.route, progress));
            if (progressBar) { progressBar.style.width = Math.round(progress * 100) + "%"; }
            if (progressText) { progressText.textContent = Math.round(progress * 100) + "% of the simulated delivery route completed."; }
            if (elapsed < 1) { state.frame = requestAnimationFrame(frame); }
        }
        state.frame = requestAnimationFrame(frame);
    }

    function showMap(element) {
        var config = configById[element.id];
        if (!config) { return; }
        var state = element._adminDelivery || buildMap(element, config);
        loadRoute(state, config);
        requestAnimationFrame(function () {
            state.map.invalidateSize();
            animateDelivery(element, state);
        });
    }

    document.querySelectorAll(".admin-track-map").forEach(function (element) {
        showMap(element);
    });
})();
