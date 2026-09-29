import SwiftUI

/// موائمات iOS 16 — الأصل كان يستخدم واجهات iOS 17 فقط.
/// نقدّم بدائل تعمل على 16 وتستعمل واجهة 17 عند توفّرها.
extension View {
    /// onChange يمرّر القيمة الجديدة — يعمل على iOS 16 (توقيع قديم) و17 (توقيع جديد).
    @ViewBuilder
    func compatOnChange<V: Equatable>(of value: V, perform action: @escaping (V) -> Void) -> some View {
        if #available(iOS 17.0, macOS 14.0, *) {
            self.onChange(of: value) { _, newValue in action(newValue) }
        } else {
            self.onChange(of: value) { newValue in action(newValue) }
        }
    }

    /// defaultScrollAnchor(.top) على iOS 17؛ لا شيء على 16 (التمرير يُدار عبر ScrollViewReader).
    @ViewBuilder
    func compatDefaultScrollAnchorTop() -> some View {
        if #available(iOS 17.0, macOS 14.0, *) {
            self.defaultScrollAnchor(.top)
        } else {
            self
        }
    }

    /// navigationDestination(item:) على iOS 17؛ على 16 نستخدم isPresented مع binding محسوب.
    @ViewBuilder
    func compatNavigationDestination<Item: Hashable, Content: View>(
        item: Binding<Item?>, @ViewBuilder destination: @escaping (Item) -> Content) -> some View {
        if #available(iOS 17.0, macOS 14.0, *) {
            self.navigationDestination(item: item, destination: destination)
        } else {
            self.navigationDestination(isPresented: Binding(
                get: { item.wrappedValue != nil },
                set: { if !$0 { item.wrappedValue = nil } }
            )) {
                if let v = item.wrappedValue { destination(v) }
            }
        }
    }
}
