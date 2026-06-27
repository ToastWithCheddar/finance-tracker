<!--
HISTORICAL — this is the original 40-day internship project report (Turkish)
describing how the app was first built. It predates the production-hardening
phase. For the current state see REPORT.md and the top-level README.md.
-->

# Personal Finance Tracker - 40 Günlük Staj Projesi Raporu

## 1. Proje Planlama ve Sistem Mimarisi Tasarımı (Günler 1-5)

### Genel Bakış

Stajımın ilk haftasında, kişisel finans yönetimi alanında kapsamlı bir web uygulaması geliştirme projesinin temellerini attım. Bu aşamada sistem mimarisi tasarımı, teknoloji seçimi ve proje planlama süreçlerini derinlemesine inceledim.

Modern mikroservis mimarisinden esinlenerek, ancak tek geliştiricinin yönetebileceği ölçekte modüler bir yapı tasarladım. Sistem üç ana katmandan oluşuyor: **İstemci Katmanı** (React PWA), **API Katmanı** (FastAPI + WebSocket), ve **Veri Katmanı** (PostgreSQL + Redis). Bu mimari sayesinde her bileşenin bağımsız geliştirilebilmesi ve test edilebilmesi sağlandı.

_[Burada sistem mimarisi diyagramı yer alacak - Client Layer, API Layer, Data Layer'ların birbirleriyle ilişkilerini gösteren detaylı diyagram]_

Teknoloji seçiminde modern web geliştirme standartlarını ve finansal uygulamaların güvenlik gereksinimlerini dikkate aldım. Ön yüz için React ve TypeScript kombinasyonu, sağlam ön uç geliştirme ve tip güvenliği sağlamak amacıyla tercih edildi. Arka yüz için FastAPI, yüksek performans ve otomatik API belgeleme yetenekleri nedeniyle seçildi. Makine öğrenmesi entegrasyonları için ise Sentence Transformers kütüphanesi, metin kategorizasyonu gibi görevlerdeki verimliliği nedeniyle projeye dahil edildi.

Geliştirme sürecinde tutarlı çalışma koşulları sağlamak amacıyla Docker tabanlı bir geliştirme ortamı kuruldu. Docker Compose kullanılarak PostgreSQL veritabanı, Redis önbellek ve mesajlaşma servisi, FastAPI arka ucu, React ön ucu, makine öğrenmesi görevleri için özel bir ML worker ve trafik yönlendirmesi için bir Nginx ters proxy gibi temel servislerin sorunsuz bir şekilde orkestrasyonu sağlandı. Bu yaklaşım, geliştirme ortamının üretim ortamını yakından taklit etmesine olanak tanıyarak güvenilirliği artırdı ve dağıtımı basitleştirdi.

_[Burada Docker Compose yapılandırması diyagramı - konteynerler arası ilişkiler]_

## 2. Veritabanı Tasarımı ve Arka Yüz Geliştirme (Günler 6-15)

Finansal verilerin karmaşıklığını yönetmek amacıyla kapsamlı bir veritabanı şeması tasarlandım. Bu süreçte, kullanıcıların finansal etkileşimlerini temel alan altı ana varlık grubu belirledim: Kullanıcılar, Hesaplar, İşlemler, Kategoriler, Bütçeler ve Hedefler. Her bir varlık arasındaki ilişkiler, veri bütünlüğünü ve tutarlılığını sağlamak için "foreign key" kısıtlamalarıyla titizlikle tanımlandım. Bu yapı, finansal verilerin doğru bir şekilde depolanmasını ve yönetilmesini sağlarken, aynı zamanda karmaşık sorguların ve raporlamanın etkin bir şekilde yapılabilmesine olanak tanıdı.

_[Burada ER (Entity-Relationship) diyagramı yer alacak - tüm tablolar ve aralarındaki ilişkiler]_

Arka uç uygulaması, modülerliği, yeniden kullanılabilirliği ve test edilebilirliği artırmak amacıyla katmanlı bir mimariyle organize edildi. Bu yapı, sorumlulukları net bir şekilde ayırarak her bir bileşenin bağımsız olarak geliştirilmesini ve sürdürülmesini kolaylaştırdı:

*   **Models:** Veritabanı etkileşimlerini yöneten SQLAlchemy ORM modellerini içerir.
*   **Schemas:** Veri doğrulama ve serileştirme için Pydantic şemalarını tanımlar.
*   **Services:** Uygulamanın temel iş mantığını barındırır.
*   **Routers:** API uç noktalarını ve ilgili HTTP metodlarını tanımlar.
*   **Dependencies:** Bağımlılık enjeksiyonu mekanizmasıyla bileşenler arası ilişkileri yönetir.

Bu katmanlı yapı, kodun daha düzenli olmasını sağlarken, aynı zamanda geliştirme sürecini hızlandırdı ve hata ayıklamayı kolaylaştırdı.

Supabase entegrasyonu ile güvenli bir kimlik doğrulama sistemi geliştirildi. JWT tabanlı oturum yönetimi kullanılarak kullanıcı kayıt, giriş, şifre sıfırlama ve çok faktörlü kimlik doğrulama özellikleri hayata geçirildi. Bu entegrasyon, kimlik doğrulama ve yetkilendirme için ölçeklenebilir bir çözüm sundu.

RESTful API tasarım ilkelerine bağlı kalarak tutarlı uç noktalar oluşturdum. FastAPI’ın otomatik Swagger belgelemesiyle interaktif ve güncel API dokümantasyonu hazırladım; her uç nokta için istek/cevap şemaları, hata kodları ve kullanım örnekleri ekledim. Bu sayede API’nin anlaşılabilirliği artırıldı.

Uygulamanın güvenilirliği için kapsamlı hata yönetimi kuruldu; özel istisnalarla anlamlı hata mesajları sağlandı ve API kötüye kullanımını önlemek amacıyla "rate limiting" mekanizmaları uygulandı.

## 3. Gerçek Zamanlı İletişim ve WebSocket Entegrasyonu (Günler 16-22)

Kullanıcıların finansal verilerini anlık olarak takip edebilmeleri için WebSocket tabanlı bir iletişim sistemi geliştirildi. Bu sistem, işlem ekleme, güncelleme, silme gibi tüm CRUD operasyonları için bir olay yayını mekanizması kurdu. Bütçe aşım uyarıları, hedef ilerleme bildirimleri ve hesap bakiye değişiklikleri gibi kritik bilgiler için anında bildirimler sağlandı. Her olay türü için farklı öncelik seviyeleri tanımlayarak, önemli bildirimlerin öncelikli olarak iletilmesi sağladım. Bir bağlantı yöneticisi oluşturularak her kullanıcının aktif bağlantıları takip ettim ve bağlantını kopması durumunda otomatik yeniden bağlanma mekanizmaları oluşturdum.

Kullanıcı çevrimdışıyken gelen mesajların kaybolmamasını sağlamak amacıyla Redis tabanlı bir mesaj deposu kuruldu. Bu sistem, mesaj kuyruklama ve teslim garantisi mekanizmalarını uygulayarak, kullanıcıların bağlantısı kesildiğinde bile önemli bildirimlerin güvenli bir şekilde saklanmasını ve yeniden bağlandıklarında teslim edilmesini sağladım. Mesaj geçmişi sınırlı bir süre saklanarak performans optimizasyonu yaptım ve sistemin verimli çalışması destekledim.

Sürekli ve güvenilir bağlantı sağlamak için bir heartbeat sistemi kuruldu. Bu sistem, ping/pong mesajları aracılığıyla bağlantı kalitesini sürekli olarak izledi. Bağlantı kopması durumlarında, `exponential backoff` algoritması kullanılarak yeniden bağlanma süresi optimize edildi. Bu sayede, ağ sorunları veya geçici kesintiler sırasında uygulamanın dayanıklılığı artırıldı ve kullanıcı deneyimi kesintisiz hale getirildi.

## 4. Makine Öğrenmesi ve Akıllı Kategorizasyon (Günler 23-28)

İşlem açıklamalarının otomatik kategorizasyonu için Sentence Transformers kütüphanesinden `all-MiniLM-L6-v2` modeli seçildi. Bu model, CPU üzerinde hızlı çalışabilme yeteneği, İngilizce metinlerdeki yüksek performansı ve model boyutu ile çıkarım hızı arasındaki optimal denge nedeniyle tercih edildi. Bu seçim, uygulamanın gerçek zamanlı kategorizasyon ihtiyaçlarını karşılamak üzere yapıldı.

Geleneksel kural tabanlı yaklaşımlar yerine, `few-shot learning` metodolojisi benimsendi. Bu yaklaşımda, her finansal kategori için az sayıda (20-40) örnek işlem açıklamasının embedding'leri hesaplanarak kategori prototipleri oluşturuldu. Yeni işlemlerin kategorizasyonu, bu prototiplerle kosinüs benzerliği hesaplanarak en yakın kategorinin belirlenmesi algoritmasıyla gerçekleştirildi. Bu yöntem, modelin yeni kategorilere hızlı adaptasyonunu sağladı ve etiketli veri ihtiyacını azalttı.

Model çıkarım hızını artırmak amacıyla ONNX runtime entegrasyonu yaptım ve bu sayede performans %50 oranında iyileştirdim. Model boyutunu küçültmek ve daha verimli çalışmasını sağlamak için "INT8 quantization" uyguladım. Çoklu işlem sınıflandırmasını optimize etmek için toplu işleme (batch processing) teknikleri kullandım ve ortalama 5ms'lik bir çıkarım süresi elde elde ettim. Bu optimizasyonlar, uygulamanın genel performansına önemli katkı sağladı.

Sınıflandırma sonuçlarının güvenilirliğini yönetmek için bir güven puanlama sistemi geliştirdim. 0.5 üzerindeki güven puanına sahip sınıflandırmalar otomatik olarak atanırken, bu eşiğin altındaki sonuçlar kullanıcı onayı gerektirdi. Kullanıcı geri bildirimleri, modelin performansını sürekli olarak iyileştirmek ve doğruluk oranını artırmak için bir öğrenme döngüsü olarak kullanıldı.

Kullanıcılara finansal verilerini kişiselleştirme esnekliği sunmak amacıyla dinamik bir kategori sistemi kurdum. Bu sistem, kullanıcıların kendi kategorilerini oluşturmasına ve mevcut kategorileri düzenlemesine olanak tanıdı. Yeni kategori örnekleri eklendiğinde, bunların embedding'leri veritabanına dahil edilerek modelin öğrenme kapasitesi sürekli olarak artırıldı ve kullanıcının özel ihtiyaçlarına daha iyi adapte olması sağlandı.

Büyük miktardaki geçmiş finansal verinin verimli bir şekilde işlenebilmesi için asenkron toplu işleme sistemi geliştirdim. Bu sistem, CSV dosyalarından yapılan toplu işlem aktarımlarında makine öğrenmesi modelinin işlemleri paralel olarak sınıflandırmasına olanak tanıdı. İşleme durumu, kullanıcılara gerçek zamanlı olarak bildirilerek şeffaflık ve kullanıcı deneyimi sağladı.

## 5. Kullanıcı Arayüzü ve Deneyim Tasarımı (Günler 29-35)

Kullanıcı arayüzü, React 18'in concurrent features özelliklerinden faydalanılarak yüksek performanslı bir şekilde geliştirdim. Yeniden kullanılabilir bileşenler, component kompozisyon prensiplerine uygun olarak oluşturmaya dikkat ettim. TypeScript kullanımıyla veri tipi güvenliği sağlayarak geliştirme süreci hızlandırdım ve bu da kod kalitesi artırdı.

Uygulamanın state yönetimi için Zustand, basit ve etkili bir global state yönetim çözümü olarak benimsendi. Sunucu tarafı state yönetimi ve önbellekleme stratejileri için TanStack Query kullandım. Yerel ve global state'in dengeli bir şekilde kullanılmasıyla performans optimizasyonu sağladım, bu da uygulamanın daha hızlı ve akıcı çalışmasına katkıda bulundu.

Finansal verilerin görselleştirilmesi için Recharts kütüphanesi kullanılarak interaktif grafikler geliştirdim. Harcama trendleri, kategori dağılımları ve bütçe takibi gibi önemli finansal göstergeleri sunmak üzere özelleştirilmiş grafik bileşenleri oluşturdum. Animasyonlu geçişlerle, kullanıcı deneyimini zenginleştirerek veri analizini daha ilgi çekici hale getirdim.

Performanslı bir form yönetimi sistemi için, React Hook Form kullandım. "Client-side" doğrulama için şema doğrulama entegrasyonunu yapılandırdım. Gerçek zamanlı hata mesajları ve alan doğrulama ile kullanıcı deneyimi iyileştirdim, bu da veri alışveriş süreçlerini hatasız ve kullanıcı dostu hale getirdi.

Uygulamanın erişilebilirliğini artırmak amacıyla klavye navigasyonu, ekran okuyucu uyumluluğu ve yüksek kontrast desteği gibi özellikler ekledim. Bu çalışmalar, uygulamanın daha geniş bir kullanıcı kitlesi tarafından rahatlıkla kullanılabilmesini sağlar.

## 6. Finansal Veri Entegrasyonu ve Plaid API (Günler 36-38)

Finansal veri entegrasyonu için Plaid Developer platformunda bir sandbox hesabı oluşturularak test ortamı kurdum. Bu süreçte, API anahtarları ve webhook URL'leri yapılandırdım. Farklı finansal senaryoları simüle etmek amacıyla test banka hesaplarını API anahtarlarıyla çektim. Bu kurulum, gerçek finansal verilerle çalışmadan önce entegrasyonun güvenli ve kontrollü bir ortamda test edilmesine yardım etti.

Güvenli banka hesabı bağlantısı için OAuth2 akışı uyguladım. Plaid Link bileşenleri React uygulamasına entegre ettim. Kullanıcı onay sürecini sorunsuz hale getirmek amacıyla adım adım ilerleyen bir "wizard" (sihirbaz) oluşturdum. Bu sayede, kullanıcıların banka hesaplarını güvenli ve kolay bir şekilde uygulamaya bağlamaları sağladım.

Kullanıcının hesaplarını otomatik olarak tanımak için banka hesabı verileri çekildi. Bu işlem senkronizasyonu için bir webhook sistemi kurdum. Aynı işlemin birden fazla eklenmesini önlemek amacıyla basit bir tekrar tespiti algoritması geliştirdim. Bu mekanizmalar, finansal verilerin doğru, güncel ve tutarlı kalmasını sağlayarak veri bütünlüğünü güvence altına aldı.

_[Burada Plaid entegrasyon akış diyagramı - OAuth flow, data sync, webhook handling]_

## 7. Test, Dağıtım ve Proje Tamamlama (Günler 39-45)

Kapsamlı test stratejisi geliştirdim: Unit testler (%60), Integration testler (%30), E2E testler (%10) oranında test coverage hedefledim. Jest ve React Testing Library ile ön yüz testleri, Pytest ile arka yüz testleri yazdım.

FastAPI TestClient kullanılarak tüm API uç noktaları için otomatik bir test paketi oluşturuldu. Harici servis bağımlılıkları, mock sistemleri aracılığıyla izole edildi. Veritabanı sorgu performans analizleri yapıldı ve eşzamanlı kullanıcı senaryolarını test etmek için yük testleri gerçekleştirildi. Bellek sızıntısı tespiti ve düzeltme işlemleriyle uygulamanın kararlılığı artırıldı.

"Multi-stage Docker build" ile hazır konteyner görüntüleri oluşturdum. Docker Compose ile yerel geliştirme ortamını üretime yakın şekilde simüle ettim. Konteyner boyutu eniyileme ve derleme süresini azaltmaya odaklandım.

Kapsamlı API belgeleri (OpenAPI/Swagger) tamamladım. Geliştirici kurulum kılavuzu ve dağıtım talimatları hazırladım. Kullanıcı kılavuzu ve özellik belgeleri oluşturdum. 

Bu 40 günlük staj projesi süresince modern web uygulaması geliştirmenin tüm aşamalarını deneyimledim. "Full-stack geliştirme", gerçek zamanlı sistemler, makine öğrenmesi entegrasyonu, finansal veri işleme ve modern DevOps practices konularında derinlemesine bilgi ve deneyim kazandım. Özellikle finansal hizmetler sektöründeki teknolojik gereksinimleri anlama ve bunlara uygun çözümler geliştirme yetkinliği edindim.