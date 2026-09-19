import Foundation
import CoreLocation

/// مدير الموقع — When In Use فقط (لا تتبع في الخلفية، لا Always افتراضيًا).
/// قراءة واحدة (requestLocation) لعرض المدينة الحقيقية + الإحداثيات عند الحاجة.
/// لا يخزّن الإحداثيات الدقيقة في أي سجل؛ تُستخدم فقط لعرض المدينة/أدوات المسافة.
final class LocationManager: NSObject, ObservableObject, CLLocationManagerDelegate {
    enum LocationStatus: Equatable {
        case notDetermined
        case denied
        case restricted
        case unavailable
        case located(city: String?)
    }

    @Published private(set) var status: LocationStatus = .notDetermined
    @Published private(set) var city: String?
    @Published private(set) var isReducedAccuracy = false
    /// إحداثيات آخر قراءة ناجحة (لا تُسجَّل، تُمرَّر فقط لمن يحتاجها).
    private(set) var lastLatitude: Double?
    private(set) var lastLongitude: Double?

    /// يُستدعى عند الحصول على إحداثيات حقيقية (لمعالجتها في بروتوكول التطبيق/السيرفر عند الحاجة).
    var onCoordinate: ((Double, Double) -> Void)?

    private let manager = CLLocationManager()
    private let geocoder = CLGeocoder()
    private let timeoutSeconds: TimeInterval = 10.0
    private var timeoutWork: DispatchWorkItem?

    override init() {
        super.init()
        manager.delegate = self
        manager.desiredAccuracy = kCLLocationAccuracyHundredMeters
    }

    /// طلب الإذن + قراءة الموقع عند الحاجة.
    func requestWhenNeeded() {
        switch manager.authorizationStatus {
        case .notDetermined:
            manager.requestWhenInUseAuthorization()
        case .authorizedWhenInUse, .authorizedAlways:
            requestLocation()
        case .denied:
            publish(.denied, city: nil)
        case .restricted:
            publish(.restricted, city: nil)
        @unknown default:
            publish(.unavailable, city: nil)
        }
    }

    private func requestLocation() {
        isReducedAccuracy = (manager.accuracyAuthorization == .reducedAccuracy)
        startTimeout()
        manager.requestLocation()   // قراءة واحدة — لا تحديث مستمر (لا تتبع في الخلفية)
    }

    private func startTimeout() {
        timeoutWork?.cancel()
        let work = DispatchWorkItem { [weak self] in
            guard let self else { return }
            if case .notDetermined = self.status {
                self.publish(.unavailable, city: nil)
            }
        }
        timeoutWork = work
        DispatchQueue.main.asyncAfter(deadline: .now() + timeoutSeconds, execute: work)
    }

    // MARK: CLLocationManagerDelegate

    func locationManagerDidChangeAuthorization(_ manager: CLLocationManager) {
        switch manager.authorizationStatus {
        case .authorizedWhenInUse, .authorizedAlways:
            requestLocation()
        case .denied:
            publish(.denied, city: nil)
        case .restricted:
            publish(.restricted, city: nil)
        case .notDetermined:
            publish(.notDetermined, city: nil)
        @unknown default:
            publish(.unavailable, city: nil)
        }
    }

    func locationManager(_ manager: CLLocationManager, didUpdateLocations locations: [CLLocation]) {
        timeoutWork?.cancel()
        guard let loc = locations.last,
              loc.horizontalAccuracy >= 0,
              abs(loc.timestamp.timeIntervalSinceNow) < 60 else {
            publish(.unavailable, city: nil)
            return
        }
        lastLatitude = loc.coordinate.latitude
        lastLongitude = loc.coordinate.longitude
        isReducedAccuracy = (manager.accuracyAuthorization == .reducedAccuracy)
        onCoordinate?(loc.coordinate.latitude, loc.coordinate.longitude)
        reverseGeocode(loc)
    }

    func locationManager(_ manager: CLLocationManager, didFailWithError error: Error) {
        timeoutWork?.cancel()
        if let err = error as? CLError {
            switch err.code {
            case .denied:
                publish(.denied, city: nil)
            case .locationUnknown:
                publish(.unavailable, city: nil)
            default:
                publish(.unavailable, city: nil)
            }
        } else {
            publish(.unavailable, city: nil)
        }
    }

    private func reverseGeocode(_ loc: CLLocation) {
        geocoder.cancelGeocode()
        geocoder.reverseGeocodeLocation(loc) { [weak self] placemarks, _ in
            guard let self else { return }
            if let place = placemarks?.first {
                let city = place.locality ?? place.administrativeArea ?? place.country
                self.publish(.located(city: city), city: city)
            } else {
                self.publish(.unavailable, city: nil)
            }
        }
    }

    /// الاسم المعروض: مدينة حقيقية، أو «الموقع غير متاح» (لا إيحاء بموقع ثابت).
    var displayCity: String {
        city ?? "الموقع غير متاح"
    }

    /// تحديث الحالة على main thread (سلامة @Published).
    private func publish(_ status: LocationStatus, city: String?) {
        DispatchQueue.main.async { [weak self] in
            self?.status = status
            self?.city = city
        }
    }
}
