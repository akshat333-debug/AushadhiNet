"""User-facing text the backend sends (WhatsApp replies, confirmation cards,
local-mode agent answers) in each supported language, plus localized names
for the 16 HMIS M19 items.

Translations were written for this project, not produced by a certified
translator; have native speakers review them before a real rollout.
"""
from __future__ import annotations

LANGS = ("en", "hi", "mr", "bn", "ta", "te", "kn")
LANG_NAMES = {"en": "English", "hi": "Hindi", "mr": "Marathi", "bn": "Bengali", "ta": "Tamil", "te": "Telugu", "kn": "Kannada"}

MESSAGES: dict[str, dict[str, str]] = {
    "en": {
        "agent_capacity": "{district} today: {full} facilities at least 90% full ({occupied} of {total} beds in use); {present} of {rostered} staff on site, {off_site} check-ins away from their facility.",
        "agent_referral": "Suggested referral: {n} patient(s) from {src} to {dst}.",
        "agent_deputation": "Suggested deputation: {n} {role} from {src} to {dst}.",
        "receipt_ok": "Receipt recorded for transfer {code}. Thank you.",
        "receipt_unknown": "No transfer {code} is on its way to this facility. Check the code in the order message.",
        "dispatch_ok": "Dispatch recorded for transfer {code}. The destination confirms with RECEIVED {code}.",
        "dispatch_unknown": "No approved transfer {code} leaves from this facility. Check the code in the order message.",
        "bad_quantity": "Not recorded: {lines}. Send whole numbers with no minus sign or decimal, e.g. 'ORS 1000'.",
        "beds_recorded": "Beds recorded for {facility}: {occupied} of {total} occupied.",
        "beds_invalid": "Occupied beds cannot be more than total beds. Send as 'BEDS <occupied>/<total>', e.g. 'BEDS 4/6'.",
        "checkin_ok": "Checked in at {facility}, {time}.",
        "checkin_far": "Checked in, but you are {km} km from {facility}. Your officer will see it flagged.",
        "not_registered": "This number is not registered to a facility.",
        "recorded": "Recorded for {facility}: {items}.",
        "unreadable": "Could not read that. Send stock as '<medicine> <quantity>', one per line, e.g. 'ORS 50'. Or send a photo of the register.",
        "confirmed_n": "Confirmed {n} record(s).",
        "nothing_pending": "Nothing waiting for confirmation.",
        "card": "Please confirm for {drug}: we're not fully sure about {fields}. Reply YES to confirm as read, or send the correct value.",
        "card_photo": "Read from your photo: {items}. Reply YES if this is right, or send the correct values as text.",
        "card_voice": "Heard in your voice note: “{heard}”. Read as: {items}. Reply YES if this is right, or send the correct values as text.",
        "field_drug_id": "which medicine this is", "field_on_hand": "the quantity",
        "field_expiry": "the expiry date", "field_batch_no": "the batch number",
        "btn_confirm": "Confirm", "btn_correct": "Correct",
        "agent_help": "I can explain a facility's risk ('why is Sinnar Phata at risk for calcium?'), list shortages ('which facilities are at risk?'), summarise beds and staff ('which facilities are full?'), or draft transfers ('propose transfers'). I cannot approve or send anything.",
        "agent_explain": "{facility}'s {drug} stock-out probability over the next week is {prob}, with expected demand around {p50} units (range {p10}-{p90}).",
        "agent_no_forecast": "No forecast available yet for {drug} at {facility}.",
        "agent_stock": "Latest stock at {facility}: {lines}.",
        "agent_no_reports": "no reports yet",
        "agent_drafted": "Drafted {n} transfer(s) for {district}. They need officer approval on the Orders page. For example: {qty} {drug} from {src} to {dst} ({minutes} min).",
        "agent_no_transfers": "No feasible transfers in {district} right now.",
        "agent_at_risk": "Most at risk in {district}: {lines}.",
        "agent_at_risk_line": "{name} ({facility}) {drug}: {on_hand} on hand vs {demand}/week",
        "agent_escalate": "Short across the whole district, so request supply from the state: {drugs}.",
        "agent_none_at_risk": "No facility in {district} is under a week of cover.",
        "agent_outside": "That is outside your jurisdiction: {detail}",
    },
    "hi": {
        "agent_capacity": "{district} आज: {full} केंद्र कम से कम 90% भरे ({total} में से {occupied} बेड उपयोग में); {rostered} में से {present} स्टाफ़ केंद्र पर, {off_site} हाज़िरी केंद्र से दूर।",
        "agent_referral": "सुझाया गया रेफ़रल: {src} से {dst} तक {n} मरीज़।",
        "agent_deputation": "सुझाई गई प्रतिनियुक्ति: {src} से {dst} तक {n} {role}।",
        "receipt_ok": "स्थानांतरण {code} की प्राप्ति दर्ज की गई। धन्यवाद।",
        "receipt_unknown": "इस केंद्र के लिए कोई स्थानांतरण {code} रास्ते में नहीं है। आदेश संदेश में कोड जाँचें।",
        "dispatch_ok": "स्थानांतरण {code} का प्रेषण दर्ज किया गया। गंतव्य केंद्र RECEIVED {code} भेजकर पुष्टि करेगा।",
        "dispatch_unknown": "इस केंद्र से कोई स्वीकृत स्थानांतरण {code} नहीं भेजा जाना है। आदेश संदेश में कोड जाँचें।",
        "bad_quantity": "दर्ज नहीं किया गया: {lines}। बिना माइनस या दशमलव के पूरी संख्या भेजें, जैसे 'ORS 1000'।",
        "beds_recorded": "{facility} के बेड दर्ज किए गए: {total} में से {occupied} भरे हैं।",
        "beds_invalid": "भरे हुए बेड कुल बेड से ज़्यादा नहीं हो सकते। 'BEDS <भरे>/<कुल>' के रूप में भेजें, जैसे 'BEDS 4/6'।",
        "checkin_ok": "{facility} पर हाज़िरी दर्ज, {time}।",
        "checkin_far": "हाज़िरी दर्ज, लेकिन आप {facility} से {km} किमी दूर हैं। आपके अधिकारी को यह चिह्नित दिखेगा।",
        "not_registered": "यह नंबर किसी स्वास्थ्य केंद्र से पंजीकृत नहीं है।",
        "recorded": "{facility} के लिए दर्ज किया गया: {items}।",
        "unreadable": "यह पढ़ा नहीं जा सका। स्टॉक '<दवा> <मात्रा>' के रूप में भेजें, हर पंक्ति में एक, जैसे 'ओआरएस 50'। या रजिस्टर की फ़ोटो भेजें।",
        "confirmed_n": "{n} प्रविष्टि(याँ) पुष्ट की गईं।",
        "nothing_pending": "पुष्टि के लिए कुछ भी लंबित नहीं है।",
        "card": "कृपया {drug} की पुष्टि करें: हमें {fields} के बारे में पूरा भरोसा नहीं है। जैसा पढ़ा गया वैसा पुष्ट करने के लिए हाँ लिखें, या सही मान भेजें।",
        "card_photo": "आपकी फ़ोटो से पढ़ा गया: {items}। सही है तो हाँ लिखें, या सही मान टेक्स्ट में भेजें।",
        "card_voice": "आपके वॉइस नोट में सुना: “{heard}”। समझा गया: {items}। सही हो तो YES भेजें, या सही मान टाइप करके भेजें।",
        "field_drug_id": "कौन-सी दवा है", "field_on_hand": "मात्रा",
        "field_expiry": "समाप्ति तिथि", "field_batch_no": "बैच संख्या",
        "btn_confirm": "पुष्टि करें", "btn_correct": "सुधारें",
        "agent_help": "मैं किसी केंद्र का जोखिम समझा सकता हूँ ('MH-0002021 में कैल्शियम गोली का जोखिम क्यों है?'), कमी वाले केंद्र बता सकता हूँ ('किन केंद्रों में जोखिम है?'), या स्थानांतरण का प्रस्ताव बना सकता हूँ ('स्थानांतरण प्रस्ताव बनाएँ')। मैं कुछ भी स्वीकृत या भेज नहीं सकता।",
        "agent_explain": "{facility} में {drug} के अगले सप्ताह ख़त्म होने की संभावना {prob} है, अपेक्षित माँग लगभग {p50} इकाई (सीमा {p10}-{p90})।",
        "agent_no_forecast": "{facility} में {drug} का पूर्वानुमान अभी उपलब्ध नहीं है।",
        "agent_stock": "{facility} का नवीनतम स्टॉक: {lines}।",
        "agent_no_reports": "अभी कोई रिपोर्ट नहीं",
        "agent_drafted": "{district} के लिए {n} स्थानांतरण प्रस्ताव बनाए गए। इन्हें ऑर्डर पेज पर अधिकारी की स्वीकृति चाहिए। उदाहरण: {src} से {dst} तक {qty} {drug} ({minutes} मिनट)।",
        "agent_no_transfers": "{district} में अभी कोई संभव स्थानांतरण नहीं है।",
        "agent_at_risk": "{district} में सबसे अधिक जोखिम: {lines}।",
        "agent_at_risk_line": "{name} ({facility}) {drug}: {on_hand} उपलब्ध, माँग {demand}/सप्ताह",
        "agent_escalate": "पूरे ज़िले में कमी, इसलिए राज्य से आपूर्ति माँगें: {drugs}।",
        "agent_none_at_risk": "{district} में किसी केंद्र का स्टॉक एक सप्ताह से कम नहीं है।",
        "agent_outside": "यह आपके अधिकार क्षेत्र से बाहर है: {detail}",
    },
    "mr": {
        "agent_capacity": "{district} आज: {full} केंद्रे किमान 90% भरलेली ({total} पैकी {occupied} बेड वापरात); {rostered} पैकी {present} कर्मचारी केंद्रावर, {off_site} हजेऱ्या केंद्रापासून दूर.",
        "agent_referral": "सुचवलेले रेफरल: {src} येथून {dst} येथे {n} रुग्ण.",
        "agent_deputation": "सुचवलेली प्रतिनियुक्ती: {src} येथून {dst} येथे {n} {role}.",
        "receipt_ok": "हस्तांतरण {code} मिळाल्याची नोंद झाली. धन्यवाद.",
        "receipt_unknown": "या केंद्रासाठी {code} हे हस्तांतरण मार्गावर नाही. आदेश संदेशातील कोड तपासा.",
        "dispatch_ok": "हस्तांतरण {code} पाठवल्याची नोंद झाली. पोहोचल्यावर गंतव्य केंद्र RECEIVED {code} पाठवेल.",
        "dispatch_unknown": "या केंद्रातून {code} हे मंजूर हस्तांतरण पाठवायचे नाही. आदेश संदेशातील कोड तपासा.",
        "bad_quantity": "नोंदवले नाही: {lines}. वजा चिन्ह किंवा दशांश नसलेली पूर्ण संख्या पाठवा, उदा. 'ORS 1000'.",
        "beds_recorded": "{facility} चे बेड नोंदवले: {total} पैकी {occupied} भरलेले.",
        "beds_invalid": "भरलेले बेड एकूण बेडपेक्षा जास्त असू शकत नाहीत. 'BEDS <भरलेले>/<एकूण>' असे पाठवा, उदा. 'BEDS 4/6'.",
        "checkin_ok": "{facility} येथे हजेरी नोंदवली, {time}.",
        "checkin_far": "हजेरी नोंदवली, पण तुम्ही {facility} पासून {km} किमी दूर आहात. तुमच्या अधिकाऱ्यांना हे चिन्हांकित दिसेल.",
        "not_registered": "हा नंबर कोणत्याही आरोग्य केंद्राशी नोंदणीकृत नाही.",
        "recorded": "{facility} साठी नोंद केली: {items}.",
        "unreadable": "हे वाचता आले नाही. साठा '<औषध> <प्रमाण>' असा पाठवा, प्रत्येक ओळीत एक, उदा. 'ओआरएस 50'. किंवा रजिस्टरचा फोटो पाठवा.",
        "confirmed_n": "{n} नोंद(दी) निश्चित केल्या.",
        "nothing_pending": "पुष्टीसाठी काहीही प्रलंबित नाही.",
        "card": "कृपया {drug} ची खात्री करा: आम्हाला {fields} बद्दल पूर्ण खात्री नाही. वाचल्याप्रमाणे निश्चित करण्यासाठी हो लिहा, किंवा योग्य मूल्य पाठवा.",
        "card_photo": "तुमच्या फोटोतून वाचले: {items}. बरोबर असल्यास हो लिहा, किंवा योग्य मूल्ये मजकुरात पाठवा.",
        "card_voice": "तुमच्या व्हॉइस नोटमध्ये ऐकले: “{heard}”. समजले: {items}. बरोबर असल्यास YES पाठवा, किंवा योग्य आकडे टाइप करून पाठवा.",
        "field_drug_id": "कोणते औषध आहे", "field_on_hand": "प्रमाण",
        "field_expiry": "कालबाह्यता तारीख", "field_batch_no": "बॅच क्रमांक",
        "btn_confirm": "निश्चित करा", "btn_correct": "दुरुस्त करा",
        "agent_help": "मी केंद्राचा धोका समजावू शकतो ('MH-0002021 मध्ये कॅल्शियम गोळीचा धोका का आहे?'), तुटवडा असलेली केंद्रे सांगू शकतो ('कोणत्या केंद्रांना धोका आहे?'), किंवा हस्तांतरणाचा प्रस्ताव तयार करू शकतो ('हस्तांतरण प्रस्ताव तयार करा'). मी काहीही मंजूर किंवा पाठवू शकत नाही.",
        "agent_explain": "{facility} मध्ये {drug} पुढील आठवड्यात संपण्याची शक्यता {prob} आहे, अपेक्षित मागणी सुमारे {p50} एकक (श्रेणी {p10}-{p90}).",
        "agent_no_forecast": "{facility} मध्ये {drug} चा अंदाज अद्याप उपलब्ध नाही.",
        "agent_stock": "{facility} येथील नवीनतम साठा: {lines}.",
        "agent_no_reports": "अद्याप अहवाल नाही",
        "agent_drafted": "{district} साठी {n} हस्तांतरण प्रस्ताव तयार केले. त्यांना ऑर्डर पानावर अधिकाऱ्याची मंजुरी हवी. उदाहरण: {src} पासून {dst} पर्यंत {qty} {drug} ({minutes} मिनिटे).",
        "agent_no_transfers": "{district} मध्ये सध्या कोणतेही शक्य हस्तांतरण नाही.",
        "agent_at_risk": "{district} मध्ये सर्वाधिक धोका: {lines}.",
        "agent_at_risk_line": "{name} ({facility}) {drug}: {on_hand} उपलब्ध, मागणी {demand}/आठवडा",
        "agent_escalate": "संपूर्ण जिल्ह्यात तुटवडा, म्हणून राज्याकडून पुरवठा मागवा: {drugs}.",
        "agent_none_at_risk": "{district} मध्ये कोणत्याही केंद्राचा साठा एका आठवड्यापेक्षा कमी नाही.",
        "agent_outside": "हे तुमच्या कार्यक्षेत्राबाहेर आहे: {detail}",
    },
    "bn": {
        "agent_capacity": "{district} আজ: {full}টি কেন্দ্র অন্তত 90% ভর্তি ({total}টির মধ্যে {occupied}টি শয্যা ব্যবহৃত); {rostered} জনের মধ্যে {present} জন কর্মী কেন্দ্রে, {off_site}টি হাজিরা কেন্দ্র থেকে দূরে।",
        "agent_referral": "প্রস্তাবিত রেফারাল: {src} থেকে {dst}-তে {n} জন রোগী।",
        "agent_deputation": "প্রস্তাবিত ডেপুটেশন: {src} থেকে {dst}-তে {n} জন {role}।",
        "receipt_ok": "স্থানান্তর {code} প্রাপ্তি নথিভুক্ত হয়েছে। ধন্যবাদ।",
        "receipt_unknown": "এই কেন্দ্রের জন্য কোনো স্থানান্তর {code} পথে নেই। আদেশ বার্তার কোডটি দেখুন।",
        "dispatch_ok": "স্থানান্তর {code} পাঠানো নথিভুক্ত হয়েছে। গন্তব্য কেন্দ্র RECEIVED {code} পাঠিয়ে নিশ্চিত করবে।",
        "dispatch_unknown": "এই কেন্দ্র থেকে কোনো অনুমোদিত স্থানান্তর {code} পাঠানোর নেই। আদেশ বার্তার কোডটি দেখুন।",
        "bad_quantity": "নথিভুক্ত হয়নি: {lines}। বিয়োগ চিহ্ন বা দশমিক ছাড়া পূর্ণ সংখ্যা পাঠান, যেমন 'ORS 1000'।",
        "beds_recorded": "{facility}-এর শয্যা নথিভুক্ত: {total}টির মধ্যে {occupied}টি ভর্তি।",
        "beds_invalid": "ভর্তি শয্যা মোট শয্যার বেশি হতে পারে না। 'BEDS <ভর্তি>/<মোট>' আকারে পাঠান, যেমন 'BEDS 4/6'।",
        "checkin_ok": "{facility}-এ হাজিরা নথিভুক্ত, {time}।",
        "checkin_far": "হাজিরা নথিভুক্ত, কিন্তু আপনি {facility} থেকে {km} কিমি দূরে। আপনার আধিকারিক এটি চিহ্নিত দেখবেন।",
        "not_registered": "এই নম্বরটি কোনো স্বাস্থ্যকেন্দ্রে নিবন্ধিত নয়।",
        "recorded": "{facility}-এর জন্য নথিভুক্ত হয়েছে: {items}।",
        "unreadable": "এটি পড়া যায়নি। মজুত '<ওষুধ> <পরিমাণ>' আকারে পাঠান, প্রতি লাইনে একটি, যেমন 'ওআরএস 50'। অথবা রেজিস্টারের ছবি পাঠান।",
        "confirmed_n": "{n}টি রেকর্ড নিশ্চিত করা হয়েছে।",
        "nothing_pending": "নিশ্চিত করার জন্য কিছুই অপেক্ষমাণ নেই।",
        "card": "অনুগ্রহ করে {drug} নিশ্চিত করুন: {fields} সম্পর্কে আমরা পুরোপুরি নিশ্চিত নই। যেমন পড়া হয়েছে তা নিশ্চিত করতে হ্যাঁ লিখুন, অথবা সঠিক মান পাঠান।",
        "card_photo": "আপনার ছবি থেকে পড়া হয়েছে: {items}। ঠিক থাকলে হ্যাঁ লিখুন, অথবা সঠিক মান লিখে পাঠান।",
        "card_voice": "আপনার ভয়েস নোটে শোনা গেছে: “{heard}”। পড়া হয়েছে: {items}। ঠিক হলে YES পাঠান, নইলে সঠিক মান লিখে পাঠান।",
        "field_drug_id": "কোন ওষুধ", "field_on_hand": "পরিমাণ",
        "field_expiry": "মেয়াদ শেষের তারিখ", "field_batch_no": "ব্যাচ নম্বর",
        "btn_confirm": "নিশ্চিত করুন", "btn_correct": "সংশোধন করুন",
        "agent_help": "আমি কোনো কেন্দ্রের ঝুঁকি ব্যাখ্যা করতে পারি ('MH-0002021-এ ক্যালসিয়াম ট্যাবলেট-এর ঝুঁকি কেন?'), ঘাটতি থাকা কেন্দ্রের তালিকা দিতে পারি ('কোন কেন্দ্রগুলো ঝুঁকিতে?'), অথবা স্থানান্তরের প্রস্তাব তৈরি করতে পারি ('স্থানান্তরের প্রস্তাব দিন')। আমি কিছু অনুমোদন বা পাঠাতে পারি না।",
        "agent_explain": "{facility}-এ আগামী সপ্তাহে {drug} শেষ হওয়ার সম্ভাবনা {prob}, প্রত্যাশিত চাহিদা প্রায় {p50} একক (পরিসর {p10}-{p90})।",
        "agent_no_forecast": "{facility}-এ {drug}-এর পূর্বাভাস এখনও নেই।",
        "agent_stock": "{facility}-এর সর্বশেষ মজুত: {lines}।",
        "agent_no_reports": "এখনও কোনো রিপোর্ট নেই",
        "agent_drafted": "{district}-এর জন্য {n}টি স্থানান্তরের প্রস্তাব তৈরি হয়েছে। অর্ডার পাতায় আধিকারিকের অনুমোদন প্রয়োজন। উদাহরণ: {src} থেকে {dst}-এ {qty} {drug} ({minutes} মিনিট)।",
        "agent_no_transfers": "{district}-এ এখন কোনো সম্ভাব্য স্থানান্তর নেই।",
        "agent_at_risk": "{district}-এ সর্বাধিক ঝুঁকি: {lines}।",
        "agent_at_risk_line": "{name} ({facility}) {drug}: মজুত {on_hand}, চাহিদা {demand}/সপ্তাহ",
        "agent_escalate": "পুরো জেলায় ঘাটতি, তাই রাজ্যের কাছে সরবরাহ চান: {drugs}।",
        "agent_none_at_risk": "{district}-এ কোনো কেন্দ্রের মজুত এক সপ্তাহের কম নয়।",
        "agent_outside": "এটি আপনার এক্তিয়ারের বাইরে: {detail}",
    },
    "ta": {
        "agent_capacity": "{district} இன்று: {full} நிலையங்கள் குறைந்தது 90% நிரம்பியுள்ளன ({total}இல் {occupied} படுக்கைகள் பயன்பாட்டில்); {rostered}இல் {present} பணியாளர்கள் நிலையத்தில், {off_site} வருகைகள் நிலையத்திலிருந்து தொலைவில்.",
        "agent_referral": "பரிந்துரைக்கப்பட்ட பரிந்துரை: {src} இலிருந்து {dst}க்கு {n} நோயாளி(கள்).",
        "agent_deputation": "பரிந்துரைக்கப்பட்ட பணி மாற்றம்: {src} இலிருந்து {dst}க்கு {n} {role}.",
        "receipt_ok": "இடமாற்றம் {code} பெறப்பட்டது பதிவு செய்யப்பட்டது. நன்றி.",
        "receipt_unknown": "இந்த நிலையத்திற்கு {code} என்ற இடமாற்றம் வரவில்லை. ஆணைச் செய்தியில் உள்ள குறியீட்டைச் சரிபார்க்கவும்.",
        "dispatch_ok": "இடமாற்றம் {code} அனுப்பப்பட்டது பதிவு செய்யப்பட்டது. சேரும் நிலையம் RECEIVED {code} என உறுதிப்படுத்தும்.",
        "dispatch_unknown": "இந்த நிலையத்திலிருந்து {code} என்ற அங்கீகரிக்கப்பட்ட இடமாற்றம் இல்லை. ஆணைச் செய்தியில் உள்ள குறியீட்டைச் சரிபார்க்கவும்.",
        "bad_quantity": "பதிவு செய்யப்படவில்லை: {lines}. கழித்தல் குறி அல்லது தசமம் இல்லாத முழு எண்ணை அனுப்பவும், எ.கா. 'ORS 1000'.",
        "beds_recorded": "{facility}க்கு படுக்கைகள் பதிவு: {total}இல் {occupied} நிரம்பியுள்ளன.",
        "beds_invalid": "நிரம்பிய படுக்கைகள் மொத்தத்தை விட அதிகமாக இருக்க முடியாது. 'BEDS <நிரம்பியவை>/<மொத்தம்>' என அனுப்பவும், எ.கா. 'BEDS 4/6'.",
        "checkin_ok": "{facility}இல் வருகை பதிவு, {time}.",
        "checkin_far": "வருகை பதிவு, ஆனால் நீங்கள் {facility}இலிருந்து {km} கி.மீ. தொலைவில் உள்ளீர்கள். உங்கள் அலுவலருக்கு இது குறிக்கப்பட்டுக் காட்டப்படும்.",
        "not_registered": "இந்த எண் எந்த சுகாதார நிலையத்திலும் பதிவு செய்யப்படவில்லை.",
        "recorded": "{facility}க்கு பதிவு செய்யப்பட்டது: {items}.",
        "unreadable": "இதைப் படிக்க முடியவில்லை. இருப்பை '<மருந்து> <அளவு>' என ஒவ்வொரு வரியிலும் ஒன்றாக அனுப்பவும், எ.கா. 'ஓஆர்எஸ் 50'. அல்லது பதிவேட்டின் புகைப்படத்தை அனுப்பவும்.",
        "confirmed_n": "{n} பதிவு(கள்) உறுதிப்படுத்தப்பட்டன.",
        "nothing_pending": "உறுதிப்படுத்த எதுவும் நிலுவையில் இல்லை.",
        "card": "{drug}க்கு உறுதிப்படுத்தவும்: {fields} பற்றி எங்களுக்கு முழு உறுதி இல்லை. படித்தபடி உறுதிப்படுத்த ஆம் என்று பதிலளிக்கவும், அல்லது சரியான மதிப்பை அனுப்பவும்.",
        "card_photo": "உங்கள் புகைப்படத்திலிருந்து படித்தது: {items}. சரி என்றால் ஆம் என்று பதிலளிக்கவும், அல்லது சரியான மதிப்புகளை உரையாக அனுப்பவும்.",
        "card_voice": "உங்கள் குரல் குறிப்பில் கேட்டது: “{heard}”. புரிந்தது: {items}. சரி என்றால் YES அனுப்பவும், இல்லையெனில் சரியான மதிப்புகளைத் தட்டச்சு செய்து அனுப்பவும்.",
        "field_drug_id": "எந்த மருந்து", "field_on_hand": "அளவு",
        "field_expiry": "காலாவதி தேதி", "field_batch_no": "தொகுதி எண்",
        "btn_confirm": "உறுதிப்படுத்து", "btn_correct": "திருத்து",
        "agent_help": "ஒரு நிலையத்தின் அபாயத்தை விளக்க முடியும் ('MH-0002021 இல் கால்சியம் மாத்திரை அபாயம் ஏன்?'), பற்றாக்குறை உள்ள நிலையங்களைப் பட்டியலிட முடியும் ('எந்த நிலையங்கள் அபாயத்தில் உள்ளன?'), அல்லது பரிமாற்ற முன்மொழிவுகளை உருவாக்க முடியும் ('பரிமாற்றங்களை முன்மொழி'). நான் எதையும் அங்கீகரிக்கவோ அனுப்பவோ முடியாது.",
        "agent_explain": "{facility} இல் அடுத்த வாரம் {drug} தீர்ந்துபோகும் வாய்ப்பு {prob}, எதிர்பார்க்கப்படும் தேவை சுமார் {p50} அலகுகள் (வரம்பு {p10}-{p90}).",
        "agent_no_forecast": "{facility} இல் {drug}க்கான முன்கணிப்பு இன்னும் இல்லை.",
        "agent_stock": "{facility} இன் சமீபத்திய இருப்பு: {lines}.",
        "agent_no_reports": "இன்னும் அறிக்கைகள் இல்லை",
        "agent_drafted": "{district}க்கு {n} பரிமாற்ற முன்மொழிவுகள் உருவாக்கப்பட்டன. ஆர்டர்கள் பக்கத்தில் அலுவலர் ஒப்புதல் தேவை. உதாரணம்: {src} இலிருந்து {dst}க்கு {qty} {drug} ({minutes} நிமிடம்).",
        "agent_no_transfers": "{district} இல் தற்போது சாத்தியமான பரிமாற்றம் இல்லை.",
        "agent_at_risk": "{district} இல் அதிக அபாயம்: {lines}.",
        "agent_at_risk_line": "{name} ({facility}) {drug}: இருப்பு {on_hand}, தேவை {demand}/வாரம்",
        "agent_escalate": "மாவட்டம் முழுவதும் பற்றாக்குறை, எனவே மாநிலத்திடம் விநியோகம் கோரவும்: {drugs}.",
        "agent_none_at_risk": "{district} இல் எந்த நிலையத்திலும் இருப்பு ஒரு வாரத்திற்குக் குறைவாக இல்லை.",
        "agent_outside": "இது உங்கள் அதிகார வரம்பிற்கு வெளியே உள்ளது: {detail}",
    },
    "te": {
        "agent_capacity": "{district} ఈరోజు: {full} కేంద్రాలు కనీసం 90% నిండాయి ({total}లో {occupied} పడకలు వాడుకలో); {rostered}లో {present} మంది సిబ్బంది కేంద్రంలో, {off_site} హాజరులు కేంద్రానికి దూరంగా.",
        "agent_referral": "సూచించిన రిఫరల్: {src} నుండి {dst}కి {n} రోగి(లు).",
        "agent_deputation": "సూచించిన డిప్యుటేషన్: {src} నుండి {dst}కి {n} {role}.",
        "receipt_ok": "బదిలీ {code} అందినట్లు నమోదైంది. ధన్యవాదాలు.",
        "receipt_unknown": "ఈ కేంద్రానికి {code} బదిలీ రావడం లేదు. ఆర్డర్ సందేశంలోని కోడ్‌ను తనిఖీ చేయండి.",
        "dispatch_ok": "బదిలీ {code} పంపినట్లు నమోదైంది. గమ్య కేంద్రం RECEIVED {code} తో నిర్ధారిస్తుంది.",
        "dispatch_unknown": "ఈ కేంద్రం నుండి {code} అనే ఆమోదిత బదిలీ లేదు. ఆర్డర్ సందేశంలోని కోడ్‌ను తనిఖీ చేయండి.",
        "bad_quantity": "నమోదు కాలేదు: {lines}. మైనస్ గుర్తు లేదా దశాంశం లేని పూర్ణ సంఖ్య పంపండి, ఉదా. 'ORS 1000'.",
        "beds_recorded": "{facility} పడకలు నమోదు: {total}లో {occupied} నిండాయి.",
        "beds_invalid": "నిండిన పడకలు మొత్తం పడకల కంటే ఎక్కువ ఉండకూడదు. 'BEDS <నిండినవి>/<మొత్తం>' రూపంలో పంపండి, ఉదా. 'BEDS 4/6'.",
        "checkin_ok": "{facility}లో హాజరు నమోదైంది, {time}.",
        "checkin_far": "హాజరు నమోదైంది, కానీ మీరు {facility} నుండి {km} కి.మీ. దూరంలో ఉన్నారు. మీ అధికారికి ఇది గుర్తించబడి కనిపిస్తుంది.",
        "not_registered": "ఈ నంబర్ ఏ ఆరోగ్య కేంద్రంలోనూ నమోదు కాలేదు.",
        "recorded": "{facility} కోసం నమోదు చేయబడింది: {items}.",
        "unreadable": "దీన్ని చదవలేకపోయాము. నిల్వను '<మందు> <పరిమాణం>' రూపంలో, ఒక్కో లైన్‌కు ఒకటి పంపండి, ఉదా. 'ఓఆర్ఎస్ 50'. లేదా రిజిస్టర్ ఫోటో పంపండి.",
        "confirmed_n": "{n} రికార్డు(లు) నిర్ధారించబడ్డాయి.",
        "nothing_pending": "నిర్ధారణ కోసం ఏదీ పెండింగ్‌లో లేదు.",
        "card": "దయచేసి {drug} నిర్ధారించండి: {fields} గురించి మాకు పూర్తి నమ్మకం లేదు. చదివినట్లే నిర్ధారించడానికి అవును అని పంపండి, లేదా సరైన విలువను పంపండి.",
        "card_photo": "మీ ఫోటో నుండి చదివినది: {items}. సరైనదైతే అవును అని పంపండి, లేదా సరైన విలువలను టెక్స్ట్\u200cగా పంపండి.",
        "card_voice": "మీ వాయిస్ నోట్‌లో విన్నది: “{heard}”. అర్థమైంది: {items}. సరైతే YES పంపండి, లేదా సరైన విలువలను టైప్ చేసి పంపండి.",
        "field_drug_id": "ఏ మందు", "field_on_hand": "పరిమాణం",
        "field_expiry": "గడువు తేదీ", "field_batch_no": "బ్యాచ్ నంబర్",
        "btn_confirm": "నిర్ధారించు", "btn_correct": "సరిచేయి",
        "agent_help": "ఒక కేంద్రం ప్రమాదాన్ని వివరించగలను ('MH-0002021 లో కాల్షియం మాత్ర ప్రమాదం ఎందుకు?'), కొరత ఉన్న కేంద్రాలను చెప్పగలను ('ఏ కేంద్రాలు ప్రమాదంలో ఉన్నాయి?'), లేదా బదిలీల ప్రతిపాదనలు తయారు చేయగలను ('బదిలీలు ప్రతిపాదించు'). నేను దేనినీ ఆమోదించలేను లేదా పంపలేను.",
        "agent_explain": "{facility} లో వచ్చే వారం {drug} అయిపోయే అవకాశం {prob}, అంచనా డిమాండ్ సుమారు {p50} యూనిట్లు (పరిధి {p10}-{p90}).",
        "agent_no_forecast": "{facility} లో {drug} అంచనా ఇంకా అందుబాటులో లేదు.",
        "agent_stock": "{facility} తాజా నిల్వ: {lines}.",
        "agent_no_reports": "ఇంకా నివేదికలు లేవు",
        "agent_drafted": "{district} కోసం {n} బదిలీ ప్రతిపాదనలు తయారయ్యాయి. ఆర్డర్ల పేజీలో అధికారి ఆమోదం అవసరం. ఉదాహరణ: {src} నుండి {dst} కు {qty} {drug} ({minutes} నిమిషాలు).",
        "agent_no_transfers": "{district} లో ప్రస్తుతం సాధ్యమయ్యే బదిలీలు లేవు.",
        "agent_at_risk": "{district} లో అత్యధిక ప్రమాదం: {lines}.",
        "agent_at_risk_line": "{name} ({facility}) {drug}: నిల్వ {on_hand}, డిమాండ్ {demand}/వారం",
        "agent_escalate": "జిల్లా అంతటా కొరత, కాబట్టి రాష్ట్రం నుండి సరఫరా కోరండి: {drugs}.",
        "agent_none_at_risk": "{district} లో ఏ కేంద్రంలోనూ నిల్వ ఒక వారం కంటే తక్కువ లేదు.",
        "agent_outside": "ఇది మీ అధికార పరిధికి వెలుపల ఉంది: {detail}",
    },
    "kn": {
        "agent_capacity": "{district} ಇಂದು: {full} ಕೇಂದ್ರಗಳು ಕನಿಷ್ಠ 90% ಭರ್ತಿ ({total}ರಲ್ಲಿ {occupied} ಹಾಸಿಗೆಗಳು ಬಳಕೆಯಲ್ಲಿ); {rostered}ರಲ್ಲಿ {present} ಸಿಬ್ಬಂದಿ ಕೇಂದ್ರದಲ್ಲಿ, {off_site} ಹಾಜರಾತಿಗಳು ಕೇಂದ್ರದಿಂದ ದೂರ.",
        "agent_referral": "ಸೂಚಿಸಿದ ರೆಫರಲ್: {src}ನಿಂದ {dst}ಗೆ {n} ರೋಗಿ(ಗಳು).",
        "agent_deputation": "ಸೂಚಿಸಿದ ನಿಯೋಜನೆ: {src}ನಿಂದ {dst}ಗೆ {n} {role}.",
        "receipt_ok": "ವರ್ಗಾವಣೆ {code} ಸ್ವೀಕೃತಿ ದಾಖಲಾಗಿದೆ. ಧನ್ಯವಾದಗಳು.",
        "receipt_unknown": "ಈ ಕೇಂದ್ರಕ್ಕೆ {code} ವರ್ಗಾವಣೆ ಬರುತ್ತಿಲ್ಲ. ಆದೇಶ ಸಂದೇಶದಲ್ಲಿನ ಕೋಡ್ ಪರಿಶೀಲಿಸಿ.",
        "dispatch_ok": "ವರ್ಗಾವಣೆ {code} ಕಳುಹಿಸಿದ್ದು ದಾಖಲಾಗಿದೆ. ತಲುಪುವ ಕೇಂದ್ರ RECEIVED {code} ಮೂಲಕ ದೃಢೀಕರಿಸುತ್ತದೆ.",
        "dispatch_unknown": "ಈ ಕೇಂದ್ರದಿಂದ {code} ಅನುಮೋದಿತ ವರ್ಗಾವಣೆ ಇಲ್ಲ. ಆದೇಶ ಸಂದೇಶದಲ್ಲಿನ ಕೋಡ್ ಪರಿಶೀಲಿಸಿ.",
        "bad_quantity": "ದಾಖಲಾಗಿಲ್ಲ: {lines}. ಮೈನಸ್ ಚಿಹ್ನೆ ಅಥವಾ ದಶಮಾಂಶ ಇಲ್ಲದ ಪೂರ್ಣ ಸಂಖ್ಯೆ ಕಳುಹಿಸಿ, ಉದಾ. 'ORS 1000'.",
        "beds_recorded": "{facility} ಹಾಸಿಗೆಗಳು ದಾಖಲಾಗಿವೆ: {total}ರಲ್ಲಿ {occupied} ಭರ್ತಿ.",
        "beds_invalid": "ಭರ್ತಿಯಾದ ಹಾಸಿಗೆಗಳು ಒಟ್ಟು ಹಾಸಿಗೆಗಳಿಗಿಂತ ಹೆಚ್ಚಿರಲು ಸಾಧ್ಯವಿಲ್ಲ. 'BEDS <ಭರ್ತಿ>/<ಒಟ್ಟು>' ಎಂದು ಕಳುಹಿಸಿ, ಉದಾ. 'BEDS 4/6'.",
        "checkin_ok": "{facility}ನಲ್ಲಿ ಹಾಜರಾತಿ ದಾಖಲಾಗಿದೆ, {time}.",
        "checkin_far": "ಹಾಜರಾತಿ ದಾಖಲಾಗಿದೆ, ಆದರೆ ನೀವು {facility}ನಿಂದ {km} ಕಿ.ಮೀ. ದೂರದಲ್ಲಿದ್ದೀರಿ. ನಿಮ್ಮ ಅಧಿಕಾರಿಗೆ ಇದು ಗುರುತಿಸಲ್ಪಟ್ಟು ಕಾಣುತ್ತದೆ.",
        "not_registered": "ಈ ಸಂಖ್ಯೆ ಯಾವುದೇ ಆರೋಗ್ಯ ಕೇಂದ್ರಕ್ಕೆ ನೋಂದಾಯಿಸಲಾಗಿಲ್ಲ.",
        "recorded": "{facility}ಗಾಗಿ ದಾಖಲಿಸಲಾಗಿದೆ: {items}.",
        "unreadable": "ಇದನ್ನು ಓದಲಾಗಲಿಲ್ಲ. ದಾಸ್ತಾನನ್ನು '<ಔಷಧ> <ಪ್ರಮಾಣ>' ರೂಪದಲ್ಲಿ, ಪ್ರತಿ ಸಾಲಿಗೆ ಒಂದು ಕಳುಹಿಸಿ, ಉದಾ. 'ಒಆರ್‌ಎಸ್ 50'. ಅಥವಾ ರಿಜಿಸ್ಟರ್‌ನ ಫೋಟೋ ಕಳುಹಿಸಿ.",
        "confirmed_n": "{n} ದಾಖಲೆ(ಗಳು) ದೃಢೀಕರಿಸಲಾಗಿದೆ.",
        "nothing_pending": "ದೃಢೀಕರಣಕ್ಕೆ ಯಾವುದೂ ಬಾಕಿ ಇಲ್ಲ.",
        "card": "ದಯವಿಟ್ಟು {drug} ದೃಢೀಕರಿಸಿ: {fields} ಬಗ್ಗೆ ನಮಗೆ ಪೂರ್ಣ ಖಚಿತತೆ ಇಲ್ಲ. ಓದಿದಂತೆ ದೃಢೀಕರಿಸಲು ಹೌದು ಎಂದು ಉತ್ತರಿಸಿ, ಅಥವಾ ಸರಿಯಾದ ಮೌಲ್ಯವನ್ನು ಕಳುಹಿಸಿ.",
        "card_photo": "ನಿಮ್ಮ ಫೋಟೋದಿಂದ ಓದಿದ್ದು: {items}. ಸರಿಯಾಗಿದ್ದರೆ ಹೌದು ಎಂದು ಉತ್ತರಿಸಿ, ಅಥವಾ ಸರಿಯಾದ ಮೌಲ್ಯಗಳನ್ನು ಪಠ್ಯವಾಗಿ ಕಳುಹಿಸಿ.",
        "card_voice": "ನಿಮ್ಮ ಧ್ವನಿ ಸಂದೇಶದಲ್ಲಿ ಕೇಳಿದ್ದು: “{heard}”. ಅರ್ಥವಾದದ್ದು: {items}. ಸರಿಯಾಗಿದ್ದರೆ YES ಕಳುಹಿಸಿ, ಇಲ್ಲವಾದರೆ ಸರಿಯಾದ ಮೌಲ್ಯಗಳನ್ನು ಟೈಪ್ ಮಾಡಿ ಕಳುಹಿಸಿ.",
        "field_drug_id": "ಯಾವ ಔಷಧ", "field_on_hand": "ಪ್ರಮಾಣ",
        "field_expiry": "ಅವಧಿ ಮುಗಿಯುವ ದಿನಾಂಕ", "field_batch_no": "ಬ್ಯಾಚ್ ಸಂಖ್ಯೆ",
        "btn_confirm": "ದೃಢೀಕರಿಸಿ", "btn_correct": "ಸರಿಪಡಿಸಿ",
        "agent_help": "ಒಂದು ಕೇಂದ್ರದ ಅಪಾಯವನ್ನು ವಿವರಿಸಬಲ್ಲೆ ('MH-0002021 ರಲ್ಲಿ ಕ್ಯಾಲ್ಸಿಯಂ ಮಾತ್ರೆ ಅಪಾಯ ಏಕೆ?'), ಕೊರತೆಯಿರುವ ಕೇಂದ್ರಗಳನ್ನು ಪಟ್ಟಿ ಮಾಡಬಲ್ಲೆ ('ಯಾವ ಕೇಂದ್ರಗಳು ಅಪಾಯದಲ್ಲಿವೆ?'), ಅಥವಾ ವರ್ಗಾವಣೆ ಪ್ರಸ್ತಾವಗಳನ್ನು ತಯಾರಿಸಬಲ್ಲೆ ('ವರ್ಗಾವಣೆ ಪ್ರಸ್ತಾವಿಸಿ'). ನಾನು ಯಾವುದನ್ನೂ ಅನುಮೋದಿಸಲು ಅಥವಾ ಕಳುಹಿಸಲು ಸಾಧ್ಯವಿಲ್ಲ.",
        "agent_explain": "{facility} ನಲ್ಲಿ ಮುಂದಿನ ವಾರ {drug} ಖಾಲಿಯಾಗುವ ಸಾಧ್ಯತೆ {prob}, ನಿರೀಕ್ಷಿತ ಬೇಡಿಕೆ ಸುಮಾರು {p50} ಘಟಕಗಳು (ವ್ಯಾಪ್ತಿ {p10}-{p90}).",
        "agent_no_forecast": "{facility} ನಲ್ಲಿ {drug}ಗೆ ಮುನ್ಸೂಚನೆ ಇನ್ನೂ ಲಭ್ಯವಿಲ್ಲ.",
        "agent_stock": "{facility} ನ ಇತ್ತೀಚಿನ ದಾಸ್ತಾನು: {lines}.",
        "agent_no_reports": "ಇನ್ನೂ ವರದಿಗಳಿಲ್ಲ",
        "agent_drafted": "{district}ಗಾಗಿ {n} ವರ್ಗಾವಣೆ ಪ್ರಸ್ತಾವಗಳನ್ನು ತಯಾರಿಸಲಾಗಿದೆ. ಆರ್ಡರ್‌ಗಳ ಪುಟದಲ್ಲಿ ಅಧಿಕಾರಿಯ ಅನುಮೋದನೆ ಬೇಕು. ಉದಾಹರಣೆ: {src} ಇಂದ {dst}ಗೆ {qty} {drug} ({minutes} ನಿಮಿಷ).",
        "agent_no_transfers": "{district} ನಲ್ಲಿ ಸದ್ಯ ಯಾವುದೇ ಸಾಧ್ಯ ವರ್ಗಾವಣೆ ಇಲ್ಲ.",
        "agent_at_risk": "{district} ನಲ್ಲಿ ಹೆಚ್ಚು ಅಪಾಯ: {lines}.",
        "agent_at_risk_line": "{name} ({facility}) {drug}: ದಾಸ್ತಾನು {on_hand}, ಬೇಡಿಕೆ {demand}/ವಾರ",
        "agent_escalate": "ಇಡೀ ಜಿಲ್ಲೆಯಲ್ಲಿ ಕೊರತೆ, ಆದ್ದರಿಂದ ರಾಜ್ಯದಿಂದ ಪೂರೈಕೆ ಕೋರಿ: {drugs}.",
        "agent_none_at_risk": "{district} ನಲ್ಲಿ ಯಾವುದೇ ಕೇಂದ್ರದ ದಾಸ್ತಾನು ಒಂದು ವಾರಕ್ಕಿಂತ ಕಡಿಮೆ ಇಲ್ಲ.",
        "agent_outside": "ಇದು ನಿಮ್ಮ ಅಧಿಕಾರ ವ್ಯಾಪ್ತಿಯ ಹೊರಗಿದೆ: {detail}",
    },
}

# Display names for the 16 HMIS M19 items (ids from ml/data/drugs.py M19_CATALOGUE).
DRUG_NAMES: dict[str, dict[str, str]] = {
    "gloves": {"en": "Gloves", "hi": "दस्ताने", "mr": "हातमोजे", "bn": "দস্তানা", "ta": "கையுறைகள்", "te": "చేతి తొడుగులు", "kn": "ಕೈಗವಸುಗಳು"},
    "mva-syringe": {"en": "MVA syringe", "hi": "एमवीए सिरिंज", "mr": "एमव्हीए सिरिंज", "bn": "এমভিএ সিরিঞ্জ", "ta": "எம்விஏ சிரிஞ்ச்", "te": "ఎంవీఏ సిరంజి", "kn": "ಎಂವಿಎ ಸಿರಿಂಜ್"},
    "fluconazole-tab": {"en": "Fluconazole tablet", "hi": "फ्लुकोनाज़ोल गोली", "mr": "फ्लुकोनाझोल गोळी", "bn": "ফ্লুকোনাজোল ট্যাবলেট", "ta": "ஃப்ளுகோனசோல் மாத்திரை", "te": "ఫ్లూకోనజోల్ మాత్ర", "kn": "ಫ್ಲುಕೊನಜೋಲ್ ಮಾತ್ರೆ"},
    "blood-transfusion-set": {"en": "Blood transfusion set", "hi": "रक्त आधान सेट", "mr": "रक्त संक्रमण संच", "bn": "রক্ত সঞ্চালন সেট", "ta": "இரத்தம் செலுத்தும் தொகுப்பு", "te": "రక్త మార్పిడి సెట్", "kn": "ರಕ್ತ ವರ್ಗಾವಣೆ ಸೆಟ್"},
    "glutaraldehyde-2pct": {"en": "Glutaraldehyde 2%", "hi": "ग्लूटाराल्डिहाइड 2%", "mr": "ग्लुटाराल्डिहाइड 2%", "bn": "গ্লুটারালডিহাইড 2%", "ta": "குளுடரால்டிஹைடு 2%", "te": "గ్లుటరాల్డిహైడ్ 2%", "kn": "ಗ್ಲುಟರಾಲ್ಡಿಹೈಡ್ 2%"},
    "ifa-adult": {"en": "IFA tablet (adult, red)", "hi": "आईएफए गोली (वयस्क, लाल)", "mr": "आयएफए गोळी (प्रौढ, लाल)", "bn": "আইএফএ ট্যাবলেট (প্রাপ্তবয়স্ক, লাল)", "ta": "ஐஎஃப்ஏ மாத்திரை (பெரியவர், சிவப்பு)", "te": "ఐఎఫ్ఏ మాత్ర (పెద్దలు, ఎరుపు)", "kn": "ಐಎಫ್‌ಎ ಮಾತ್ರೆ (ವಯಸ್ಕರು, ಕೆಂಪು)"},
    "ifa-blue": {"en": "IFA tablet (adolescent, blue)", "hi": "आईएफए गोली (किशोर, नीली)", "mr": "आयएफए गोळी (किशोर, निळी)", "bn": "আইএফএ ট্যাবলেট (কিশোর, নীল)", "ta": "ஐஎஃப்ஏ மாத்திரை (வளரிளம், நீலம்)", "te": "ఐఎఫ్ఏ మాత్ర (కౌమారులు, నీలం)", "kn": "ಐಎಫ್‌ಎ ಮಾತ್ರೆ (ಹದಿಹರೆಯ, ನೀಲಿ)"},
    "ifa-pink": {"en": "IFA tablet (junior, pink)", "hi": "आईएफए गोली (बाल, गुलाबी)", "mr": "आयएफए गोळी (बाल, गुलाबी)", "bn": "আইএফএ ট্যাবলেট (শিশু, গোলাপি)", "ta": "ஐஎஃப்ஏ மாத்திரை (சிறார், இளஞ்சிவப்பு)", "te": "ఐఎఫ్ఏ మాత్ర (పిల్లలు, గులాబీ)", "kn": "ಐಎಫ್‌ಎ ಮಾತ್ರೆ (ಮಕ್ಕಳು, ಗುಲಾಬಿ)"},
    "ifa-syrup": {"en": "IFA syrup (paediatric)", "hi": "आईएफए सिरप (शिशु)", "mr": "आयएफए सिरप (बालकांसाठी)", "bn": "আইএফএ সিরাপ (শিশু)", "ta": "ஐஎஃப்ஏ சிரப் (குழந்தைகள்)", "te": "ఐఎఫ్ఏ సిరప్ (శిశువులు)", "kn": "ಐಎಫ್‌ಎ ಸಿರಪ್ (ಶಿಶುಗಳು)"},
    "paed-antibiotics": {"en": "Paediatric antibiotics", "hi": "बाल एंटीबायोटिक", "mr": "बाल प्रतिजैविके", "bn": "শিশুদের অ্যান্টিবায়োটিক", "ta": "குழந்தைகள் நுண்ணுயிர் எதிர்ப்பிகள்", "te": "పిల్లల యాంటీబయాటిక్స్", "kn": "ಮಕ್ಕಳ ಪ್ರತಿಜೀವಕಗಳು"},
    "vitamin-a-syrup": {"en": "Vitamin A syrup", "hi": "विटामिन ए सिरप", "mr": "जीवनसत्त्व अ सिरप", "bn": "ভিটামিন এ সিরাপ", "ta": "வைட்டமின் ஏ சிரப்", "te": "విటమిన్ ఎ సిరప్", "kn": "ವಿಟಮಿನ್ ಎ ಸಿರಪ್"},
    "ors": {"en": "ORS", "hi": "ओआरएस", "mr": "ओआरएस", "bn": "ওআরএস", "ta": "ஓஆர்எஸ்", "te": "ఓఆర్ఎస్", "kn": "ಒಆರ್‌ಎಸ್"},
    "rti-sti-kit": {"en": "RTI/STI kit", "hi": "आरटीआई/एसटीआई किट", "mr": "आरटीआय/एसटीआय किट", "bn": "আরটিআই/এসটিআই কিট", "ta": "ஆர்டிஐ/எஸ்டிஐ கிட்", "te": "ఆర్టీఐ/ఎస్టీఐ కిట్", "kn": "ಆರ್‌ಟಿಐ/ಎಸ್‌ಟಿಐ ಕಿಟ್"},
    "zinc-20mg": {"en": "Zinc 20 mg tablet", "hi": "ज़िंक 20 मि.ग्रा. गोली", "mr": "झिंक 20 मि.ग्रॅ. गोळी", "bn": "জিঙ্ক 20 মি.গ্রা. ট্যাবলেট", "ta": "ஜிங்க் 20 மி.கி. மாத்திரை", "te": "జింక్ 20 మి.గ్రా. మాత్ర", "kn": "ಜಿಂಕ್ 20 ಮಿ.ಗ್ರಾಂ ಮಾತ್ರೆ"},
    "albendazole-400mg": {"en": "Albendazole 400 mg", "hi": "एल्बेंडाज़ोल 400 मि.ग्रा.", "mr": "अल्बेंडाझोल 400 मि.ग्रॅ.", "bn": "অ্যালবেনডাজোল 400 মি.গ্রা.", "ta": "அல்பெண்டசோல் 400 மி.கி.", "te": "ఆల్బెండజోల్ 400 మి.గ్రా.", "kn": "ಆಲ್ಬೆಂಡಜೋಲ್ 400 ಮಿ.ಗ್ರಾಂ"},
    "calcium-tab": {"en": "Calcium tablet", "hi": "कैल्शियम गोली", "mr": "कॅल्शियम गोळी", "bn": "ক্যালসিয়াম ট্যাবলেট", "ta": "கால்சியம் மாத்திரை", "te": "కాల్షియం మాత్ర", "kn": "ಕ್ಯಾಲ್ಸಿಯಂ ಮಾತ್ರೆ"},
}

PLACE_NAMES: dict[str, dict[str, str]] = {
    "nashik": {"en": "Nashik", "hi": "नासिक", "mr": "नाशिक", "bn": "নাসিক", "ta": "நாசிக்", "te": "నాసిక్", "kn": "ನಾಸಿಕ್"},
    "dhule": {"en": "Dhule", "hi": "धुले", "mr": "धुळे", "bn": "ধুলে", "ta": "துலே", "te": "ధూలే", "kn": "ಧುಲೆ"},
}


def place_name(district_id: str, lang: str | None) -> str:
    slug = district_id.split("/")[-1]
    names = PLACE_NAMES.get(slug)
    return (names.get(norm_lang(lang)) or names["en"]) if names else slug.replace("_", " ").title()


# Words a reporter types to confirm a pending record, in any supported language.
CONFIRM_WORDS = {"YES", "Y", "CONFIRM", "OK", "हाँ", "हां", "हो", "হ্যাঁ", "ஆம்", "అవును", "ಹೌದು"}

# Intent keywords for the local-mode agent (cloud mode uses Gemini, which reads any language).
INTENT_WORDS = {
    "propose": ("propose", "draft", "transfer", "redistribut", "प्रस्ताव", "स्थानांतरण", "हस्तांतरण", "প্রস্তাব", "স্থানান্তর", "பரிமாற்ற", "முன்மொழி", "బదిలీ", "ప్రతిపాద", "ವರ್ಗಾವಣೆ", "ಪ್ರಸ್ತಾವ"),
    "capacity": ("bed", "staff", "attendance", "check-in", "checked in", "checkin", "off-site", "referral", "deput", "absent", "full",
                 "बेड", "स्टाफ", "हाज़िर", "हाजिर", "हजेरी", "कर्मचारी", "শয্যা", "কর্মী", "படுக்கை", "பணியாளர்", "పడక", "సిబ్బంది", "ಹಾಸಿಗೆ", "ಸಿಬ್ಬಂದಿ"),
    # Requests to act are refused before any model sees them: the agent has no tool to act anyway.
    "action": ("approv", "send ", "sign the", "sign all", "execute", "dispatch", "मंजूर", "भेजो", "भेजें", "पाठवा", "অনুমোদন", "ஒப்புத", "ఆమోద", "ಅನುಮೋದ"),
    "risk": ("risk", "shortage", "stock-out", "stockout", "running out", "low", "जोखिम", "कमी", "धोका", "तुटवडा", "ঝুঁকি", "ঘাটতি", "அபாய", "பற்றாக்குறை", "ప్రమాద", "కొరత", "ಅಪಾಯ", "ಕೊರತೆ"),
}


def norm_lang(lang: str | None) -> str:
    return lang if lang in LANGS else "en"


def msg(lang: str | None, key: str, **kwargs) -> str:
    template = MESSAGES[norm_lang(lang)].get(key) or MESSAGES["en"][key]
    return template.format(**kwargs)


def drug_name(drug_id: str, lang: str | None) -> str:
    names = DRUG_NAMES.get(drug_id)
    if not names:
        return drug_id
    return names.get(norm_lang(lang)) or names["en"]


# Common medicines outside the 16-item pilot catalogue that nurses still write down;
# names only (for matching reads), not shown in the UI.
EXTRA_LOCAL_NAMES: dict[str, dict[str, str]] = {
    "paracetamol": {"hi": "पैरासिटामोल", "mr": "पॅरासिटामॉल", "bn": "প্যারাসিটামল", "ta": "பாராசிட்டமால்", "te": "పారాసిటమాల్", "kn": "ಪ್ಯಾರಸಿಟಮಾಲ್"},
}


def _local_aliases() -> dict[str, str]:
    """Localized name -> drug id, plus each name's first word when that word is unambiguous
    (so "झिंक" finds zinc, but "आयएफए" alone, shared by four IFA products, finds nothing)."""
    aliases: dict[str, str] = {}
    first_words: dict[str, set[str]] = {}
    for drug_id, names in {**DRUG_NAMES, **EXTRA_LOCAL_NAMES}.items():
        for lang, name in names.items():
            if lang == "en":
                continue
            aliases[name.lower()] = drug_id
            first_words.setdefault(name.split()[0].lower(), set()).add(drug_id)
    for word, ids in first_words.items():
        if len(ids) == 1:
            aliases.setdefault(word, next(iter(ids)))
    return aliases


LOCAL_ALIASES = _local_aliases()


def find_local_drug(text: str) -> str | None:
    """Drug id for a localized medicine name contained in `text`, longest match first."""
    lowered = text.lower()
    for alias in sorted(LOCAL_ALIASES, key=len, reverse=True):
        if alias in lowered:
            return LOCAL_ALIASES[alias]
    return None
