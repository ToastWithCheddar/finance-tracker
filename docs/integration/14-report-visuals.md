# 14 — Rapor için Görseller (6 Şekil)

## Summary

`REPORT.md` (12 bölüm) için 6 figürden oluşan dengeli bir görsel set
eklendi: 3 mimari / veri / metrik diyagramı (Mermaid), 1 mevcut konteyner
topolojisi diyagramının yeniden referansı, ve 2 UI ekran görüntüsü
(operatörün canlı çalıştırmada yakalayacağı). Amaç: yapısal anlayış +
çalışan uygulama kanıtı + sertleştirmenin ölçülebilir etkisi.

## Files added

| Path | Purpose |
|---|---|
| `docs/audit/diagrams/01-system-architecture.md` | Şekil 1 — Yüksek seviye sistem mimarisi (Mermaid `flowchart LR`). |
| `docs/audit/diagrams/02-er-diagram.md` | Şekil 2 — Çekirdek tablolar ER diyagramı (Mermaid `erDiagram`). |
| `docs/audit/diagrams/06-perf-before-after.md` | Şekil 6 — Faz öncesi/sonrası yapısal metrikler ve risk kaydı kapanması (Mermaid `xychart-beta` + tablo fallback). |
| `docs/audit/screenshots/README.md` | Şekil 4 ve 5 PNG'lerinin yerleşim notu. |
| `docs/integration/14-report-visuals.md` | Bu changelog. |

## Files edited

| Path | Change |
|---|---|
| `REPORT.md` | "Şekiller" mini-indeksi giriş paragrafından sonra eklendi; Şekil 1 §1'e, Şekil 2 §2'ye, Şekil 5 §7'ye (ML), Şekil 3 §5'e (Üretim Hazırlığı), Şekil 4 §3'ün hemen üstüne (ekran kanıtı), Şekil 6 §12'ye (Sayısal Özet) yerleştirildi. Tüm referanslar göreceli markdown bağlantılarıyla. |

## Files reused as-is

| Path | Purpose |
|---|---|
| `docs/audit/diagrams/prod-compose.md` | Şekil 3 — Üretim konteyner topolojisi. |

## Operator-captured screenshots (henüz dosyada yok)

Aşağıdaki iki PNG **operatör tarafından** `make prod-up` sağlıklı duruma
ulaştıktan sonra yakalanıp belirtilen yola konulmalıdır.

### Şekil 4 — Dashboard

- **Yol:** `docs/audit/screenshots/04-dashboard.png`
- **Adımlar:**
  1. `make prod-up` → tüm konteynerler `healthy`.
  2. Tarayıcı: `https://localhost/`, kendi kendine imzalı sertifikayı
     kabul et, oturum aç, Dashboard'a düş.
  3. Pencere boyutu 1280×800, %100 zoom, light theme.
  4. Şu öğeler görünür olmalı: üst bar (kullanıcı adı + bildirim),
     4 adet MetricCard (gelir / gider / tasarruf / bütçe), kategori
     dağılım grafiği, son işlemler paneli.
  5. macOS: `Shift+Cmd+4` → space → tarayıcı penceresine tıkla.

### Şekil 5 — Transactions + ML Kategorileri

- **Yol:** `docs/audit/screenshots/05-transactions-ml.png`
- **Adımlar:**
  1. Sol menüden `Transactions`.
  2. ML rozet sütununun görünür olduğu en az 10 işlem listele
     (güven kovası rengi: yeşil / sarı / turuncu / kırmızı).
  3. Aynı pencere boyutu ve tema.
  4. Tek bir işlem üzerine gelip `ml_suggested_category_id` tooltipi
     görünüyorsa onu da gösteren bir ekran tercih edilir.

PNG'leri yerleştirdikten sonra `REPORT.md` zaten ilgili yollara referans
verdiği için tekrar düzenlemeye gerek yok.

## Verification

- [x] `docs/audit/diagrams/{01-system-architecture,02-er-diagram,06-perf-before-after}.md` mevcut ve Mermaid blokları sentaks açısından kapalı.
- [x] `docs/audit/screenshots/README.md` mevcut.
- [x] `REPORT.md` içinde 6 figür referansı (her şekil için bir `![…](…)` veya `[Şekil N](…)` bağlantısı) var.
- [ ] (Operatör) `04-dashboard.png` ve `05-transactions-ml.png` yerleştirildi.
- [ ] (Operatör) GitHub'da REPORT.md önizlemesi açıldığında her Mermaid bloğu render oluyor (özellikle `xychart-beta` — render etmezse tablo fallback'i zaten yanında).

## Open follow-ups

- Operatör iki PNG'yi yakalayıp commit ederse şekil seti tamamlanır.
- Canlı benchmark çıktıları geldiğinde Şekil 6'ya §6c başlığı altında somut p95 / LCP / inferans rakamları eklenecek; bu rapor güncellemesi `docs/audit/metrics/runtime.md` ile eşzamanlı yapılmalıdır.
