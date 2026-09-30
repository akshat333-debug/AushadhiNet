"""User-facing text the backend sends (WhatsApp replies, confirmation cards,
local-mode agent answers) in each supported language, plus localized names
for the 16 HMIS M19 items.

Translations were written for this project, not produced by a certified
translator; have native speakers review them before a real rollout.
"""
from __future__ import annotations

LANGS = ("en", "hi", "mr", "bn", "ta", "te", "kn")

MESSAGES: dict[str, dict[str, str]] = {
    "en": {
        "not_registered": "This number is not registered to a facility.",
        "recorded": "Recorded for {facility}: {items}.",
        "unreadable": "Could not read that. Send stock as '<medicine> <quantity>', one per line, e.g. 'ORS 50'. Or send a photo of the register.",
        "confirmed_n": "Confirmed {n} record(s).",
        "nothing_pending": "Nothing waiting for confirmation.",
        "card": "Please confirm for {drug}: we're not fully sure about {fields}. Reply YES to confirm as read, or send the correct value.",
        "field_drug_id": "which medicine this is", "field_on_hand": "the quantity",
        "field_expiry": "the expiry date", "field_batch_no": "the batch number",
        "btn_confirm": "Confirm", "btn_correct": "Correct",
        "agent_help": "I can explain a facility's risk ('why is MH-0000221 at risk for ORS?'), list shortages ('which facilities are at risk?'), or draft transfers ('propose transfers'). I cannot approve or send anything.",
        "agent_explain": "{facility}'s {drug} stock-out probability over the next week is {prob}, with expected demand around {p50} units (range {p10}-{p90}).",
        "agent_no_forecast": "No forecast available yet for {drug} at {facility}.",
        "agent_stock": "Latest stock at {facility}: {lines}.",
        "agent_no_reports": "no reports yet",
        "agent_drafted": "Drafted {n} transfer(s) for {district}. They need officer approval on the Orders page. For example: {qty} {drug} from {src} to {dst} ({minutes} min).",
        "agent_no_transfers": "No feasible transfers in {district} right now.",
        "agent_at_risk": "Most at risk in {district}: {lines}.",
        "agent_at_risk_line": "{name} ({facility}) {drug}: {on_hand} on hand vs {demand}/week",
        "agent_none_at_risk": "No facility in {district} is under a week of cover.",
        "agent_outside": "That is outside your jurisdiction: {detail}",
    },
    "hi": {
        "not_registered": "यह नंबर किसी स्वास्थ्य केंद्र से पंजीकृत नहीं है।",
        "recorded": "{facility} के लिए दर्ज किया गया: {items}।",
        "unreadable": "यह पढ़ा नहीं जा सका। स्टॉक '<दवा> <मात्रा>' के रूप में भेजें, हर पंक्ति में एक, जैसे 'ओआरएस 50'। या रजिस्टर की फ़ोटो भेजें।",
        "confirmed_n": "{n} प्रविष्टि(याँ) पुष्ट की गईं।",
        "nothing_pending": "पुष्टि के लिए कुछ भी लंबित नहीं है।",
        "card": "कृपया {drug} की पुष्टि करें: हमें {fields} के बारे में पूरा भरोसा नहीं है। जैसा पढ़ा गया वैसा पुष्ट करने के लिए हाँ लिखें, या सही मान भेजें।",
        "field_drug_id": "कौन-सी दवा है", "field_on_hand": "मात्रा",
        "field_expiry": "समाप्ति तिथि", "field_batch_no": "बैच संख्या",
        "btn_confirm": "पुष्टि करें", "btn_correct": "सुधारें",
        "agent_help": "मैं किसी केंद्र का जोखिम समझा सकता हूँ ('MH-0000221 में ओआरएस का जोखिम क्यों है?'), कमी वाले केंद्र बता सकता हूँ ('किन केंद्रों में जोखिम है?'), या स्थानांतरण का प्रस्ताव बना सकता हूँ ('स्थानांतरण प्रस्ताव बनाएँ')। मैं कुछ भी स्वीकृत या भेज नहीं सकता।",
        "agent_explain": "{facility} में {drug} के अगले सप्ताह ख़त्म होने की संभावना {prob} है, अपेक्षित माँग लगभग {p50} इकाई (सीमा {p10}-{p90})।",
        "agent_no_forecast": "{facility} में {drug} का पूर्वानुमान अभी उपलब्ध नहीं है।",
        "agent_stock": "{facility} का नवीनतम स्टॉक: {lines}।",
        "agent_no_reports": "अभी कोई रिपोर्ट नहीं",
        "agent_drafted": "{district} के लिए {n} स्थानांतरण प्रस्ताव बनाए गए। इन्हें ऑर्डर पेज पर अधिकारी की स्वीकृति चाहिए। उदाहरण: {src} से {dst} तक {qty} {drug} ({minutes} मिनट)।",
        "agent_no_transfers": "{district} में अभी कोई संभव स्थानांतरण नहीं है।",
        "agent_at_risk": "{district} में सबसे अधिक जोखिम: {lines}।",
        "agent_at_risk_line": "{name} ({facility}) {drug}: {on_hand} उपलब्ध, माँग {demand}/सप्ताह",
        "agent_none_at_risk": "{district} में किसी केंद्र का स्टॉक एक सप्ताह से कम नहीं है।",
        "agent_outside": "यह आपके अधिकार क्षेत्र से बाहर है: {detail}",
    },
    "mr": {
        "not_registered": "हा नंबर कोणत्याही आरोग्य केंद्राशी नोंदणीकृत नाही.",
        "recorded": "{facility} साठी नोंद केली: {items}.",
        "unreadable": "हे वाचता आले नाही. साठा '<औषध> <प्रमाण>' असा पाठवा, प्रत्येक ओळीत एक, उदा. 'ओआरएस 50'. किंवा रजिस्टरचा फोटो पाठवा.",
        "confirmed_n": "{n} नोंद(दी) निश्चित केल्या.",
        "nothing_pending": "पुष्टीसाठी काहीही प्रलंबित नाही.",
        "card": "कृपया {drug} ची खात्री करा: आम्हाला {fields} बद्दल पूर्ण खात्री नाही. वाचल्याप्रमाणे निश्चित करण्यासाठी हो लिहा, किंवा योग्य मूल्य पाठवा.",
        "field_drug_id": "कोणते औषध आहे", "field_on_hand": "प्रमाण",
        "field_expiry": "कालबाह्यता तारीख", "field_batch_no": "बॅच क्रमांक",
        "btn_confirm": "निश्चित करा", "btn_correct": "दुरुस्त करा",
        "agent_help": "मी केंद्राचा धोका समजावू शकतो ('MH-0000221 मध्ये ओआरएसचा धोका का आहे?'), तुटवडा असलेली केंद्रे सांगू शकतो ('कोणत्या केंद्रांना धोका आहे?'), किंवा हस्तांतरणाचा प्रस्ताव तयार करू शकतो ('हस्तांतरण प्रस्ताव तयार करा'). मी काहीही मंजूर किंवा पाठवू शकत नाही.",
        "agent_explain": "{facility} मध्ये {drug} पुढील आठवड्यात संपण्याची शक्यता {prob} आहे, अपेक्षित मागणी सुमारे {p50} एकक (श्रेणी {p10}-{p90}).",
        "agent_no_forecast": "{facility} मध्ये {drug} चा अंदाज अद्याप उपलब्ध नाही.",
        "agent_stock": "{facility} येथील नवीनतम साठा: {lines}.",
        "agent_no_reports": "अद्याप अहवाल नाही",
        "agent_drafted": "{district} साठी {n} हस्तांतरण प्रस्ताव तयार केले. त्यांना ऑर्डर पानावर अधिकाऱ्याची मंजुरी हवी. उदाहरण: {src} पासून {dst} पर्यंत {qty} {drug} ({minutes} मिनिटे).",
        "agent_no_transfers": "{district} मध्ये सध्या कोणतेही शक्य हस्तांतरण नाही.",
        "agent_at_risk": "{district} मध्ये सर्वाधिक धोका: {lines}.",
        "agent_at_risk_line": "{name} ({facility}) {drug}: {on_hand} उपलब्ध, मागणी {demand}/आठवडा",
        "agent_none_at_risk": "{district} मध्ये कोणत्याही केंद्राचा साठा एका आठवड्यापेक्षा कमी नाही.",
        "agent_outside": "हे तुमच्या कार्यक्षेत्राबाहेर आहे: {detail}",
    },
    "bn": {
        "not_registered": "এই নম্বরটি কোনো স্বাস্থ্যকেন্দ্রে নিবন্ধিত নয়।",
        "recorded": "{facility}-এর জন্য নথিভুক্ত হয়েছে: {items}।",
        "unreadable": "এটি পড়া যায়নি। মজুত '<ওষুধ> <পরিমাণ>' আকারে পাঠান, প্রতি লাইনে একটি, যেমন 'ওআরএস 50'। অথবা রেজিস্টারের ছবি পাঠান।",
        "confirmed_n": "{n}টি রেকর্ড নিশ্চিত করা হয়েছে।",
        "nothing_pending": "নিশ্চিত করার জন্য কিছুই অপেক্ষমাণ নেই।",
        "card": "অনুগ্রহ করে {drug} নিশ্চিত করুন: {fields} সম্পর্কে আমরা পুরোপুরি নিশ্চিত নই। যেমন পড়া হয়েছে তা নিশ্চিত করতে হ্যাঁ লিখুন, অথবা সঠিক মান পাঠান।",
        "field_drug_id": "কোন ওষুধ", "field_on_hand": "পরিমাণ",
        "field_expiry": "মেয়াদ শেষের তারিখ", "field_batch_no": "ব্যাচ নম্বর",
        "btn_confirm": "নিশ্চিত করুন", "btn_correct": "সংশোধন করুন",
        "agent_help": "আমি কোনো কেন্দ্রের ঝুঁকি ব্যাখ্যা করতে পারি ('MH-0000221-এ ওআরএস-এর ঝুঁকি কেন?'), ঘাটতি থাকা কেন্দ্রের তালিকা দিতে পারি ('কোন কেন্দ্রগুলো ঝুঁকিতে?'), অথবা স্থানান্তরের প্রস্তাব তৈরি করতে পারি ('স্থানান্তরের প্রস্তাব দিন')। আমি কিছু অনুমোদন বা পাঠাতে পারি না।",
        "agent_explain": "{facility}-এ আগামী সপ্তাহে {drug} শেষ হওয়ার সম্ভাবনা {prob}, প্রত্যাশিত চাহিদা প্রায় {p50} একক (পরিসর {p10}-{p90})।",
        "agent_no_forecast": "{facility}-এ {drug}-এর পূর্বাভাস এখনও নেই।",
        "agent_stock": "{facility}-এর সর্বশেষ মজুত: {lines}।",
        "agent_no_reports": "এখনও কোনো রিপোর্ট নেই",
        "agent_drafted": "{district}-এর জন্য {n}টি স্থানান্তরের প্রস্তাব তৈরি হয়েছে। অর্ডার পাতায় আধিকারিকের অনুমোদন প্রয়োজন। উদাহরণ: {src} থেকে {dst}-এ {qty} {drug} ({minutes} মিনিট)।",
        "agent_no_transfers": "{district}-এ এখন কোনো সম্ভাব্য স্থানান্তর নেই।",
        "agent_at_risk": "{district}-এ সর্বাধিক ঝুঁকি: {lines}।",
        "agent_at_risk_line": "{name} ({facility}) {drug}: মজুত {on_hand}, চাহিদা {demand}/সপ্তাহ",
        "agent_none_at_risk": "{district}-এ কোনো কেন্দ্রের মজুত এক সপ্তাহের কম নয়।",
        "agent_outside": "এটি আপনার এক্তিয়ারের বাইরে: {detail}",
    },
    "ta": {
        "not_registered": "இந்த எண் எந்த சுகாதார நிலையத்திலும் பதிவு செய்யப்படவில்லை.",
        "recorded": "{facility}க்கு பதிவு செய்யப்பட்டது: {items}.",
        "unreadable": "இதைப் படிக்க முடியவில்லை. இருப்பை '<மருந்து> <அளவு>' என ஒவ்வொரு வரியிலும் ஒன்றாக அனுப்பவும், எ.கா. 'ஓஆர்எஸ் 50'. அல்லது பதிவேட்டின் புகைப்படத்தை அனுப்பவும்.",
        "confirmed_n": "{n} பதிவு(கள்) உறுதிப்படுத்தப்பட்டன.",
        "nothing_pending": "உறுதிப்படுத்த எதுவும் நிலுவையில் இல்லை.",
        "card": "{drug}க்கு உறுதிப்படுத்தவும்: {fields} பற்றி எங்களுக்கு முழு உறுதி இல்லை. படித்தபடி உறுதிப்படுத்த ஆம் என்று பதிலளிக்கவும், அல்லது சரியான மதிப்பை அனுப்பவும்.",
        "field_drug_id": "எந்த மருந்து", "field_on_hand": "அளவு",
        "field_expiry": "காலாவதி தேதி", "field_batch_no": "தொகுதி எண்",
        "btn_confirm": "உறுதிப்படுத்து", "btn_correct": "திருத்து",
        "agent_help": "ஒரு நிலையத்தின் அபாயத்தை விளக்க முடியும் ('MH-0000221 இல் ஓஆர்எஸ் அபாயம் ஏன்?'), பற்றாக்குறை உள்ள நிலையங்களைப் பட்டியலிட முடியும் ('எந்த நிலையங்கள் அபாயத்தில் உள்ளன?'), அல்லது பரிமாற்ற முன்மொழிவுகளை உருவாக்க முடியும் ('பரிமாற்றங்களை முன்மொழி'). நான் எதையும் அங்கீகரிக்கவோ அனுப்பவோ முடியாது.",
        "agent_explain": "{facility} இல் அடுத்த வாரம் {drug} தீர்ந்துபோகும் வாய்ப்பு {prob}, எதிர்பார்க்கப்படும் தேவை சுமார் {p50} அலகுகள் (வரம்பு {p10}-{p90}).",
        "agent_no_forecast": "{facility} இல் {drug}க்கான முன்கணிப்பு இன்னும் இல்லை.",
        "agent_stock": "{facility} இன் சமீபத்திய இருப்பு: {lines}.",
        "agent_no_reports": "இன்னும் அறிக்கைகள் இல்லை",
        "agent_drafted": "{district}க்கு {n} பரிமாற்ற முன்மொழிவுகள் உருவாக்கப்பட்டன. ஆர்டர்கள் பக்கத்தில் அலுவலர் ஒப்புதல் தேவை. உதாரணம்: {src} இலிருந்து {dst}க்கு {qty} {drug} ({minutes} நிமிடம்).",
        "agent_no_transfers": "{district} இல் தற்போது சாத்தியமான பரிமாற்றம் இல்லை.",
        "agent_at_risk": "{district} இல் அதிக அபாயம்: {lines}.",
        "agent_at_risk_line": "{name} ({facility}) {drug}: இருப்பு {on_hand}, தேவை {demand}/வாரம்",
        "agent_none_at_risk": "{district} இல் எந்த நிலையத்திலும் இருப்பு ஒரு வாரத்திற்குக் குறைவாக இல்லை.",
        "agent_outside": "இது உங்கள் அதிகார வரம்பிற்கு வெளியே உள்ளது: {detail}",
    },
    "te": {
        "not_registered": "ఈ నంబర్ ఏ ఆరోగ్య కేంద్రంలోనూ నమోదు కాలేదు.",
        "recorded": "{facility} కోసం నమోదు చేయబడింది: {items}.",
        "unreadable": "దీన్ని చదవలేకపోయాము. నిల్వను '<మందు> <పరిమాణం>' రూపంలో, ఒక్కో లైన్‌కు ఒకటి పంపండి, ఉదా. 'ఓఆర్ఎస్ 50'. లేదా రిజిస్టర్ ఫోటో పంపండి.",
        "confirmed_n": "{n} రికార్డు(లు) నిర్ధారించబడ్డాయి.",
        "nothing_pending": "నిర్ధారణ కోసం ఏదీ పెండింగ్‌లో లేదు.",
        "card": "దయచేసి {drug} నిర్ధారించండి: {fields} గురించి మాకు పూర్తి నమ్మకం లేదు. చదివినట్లే నిర్ధారించడానికి అవును అని పంపండి, లేదా సరైన విలువను పంపండి.",
        "field_drug_id": "ఏ మందు", "field_on_hand": "పరిమాణం",
        "field_expiry": "గడువు తేదీ", "field_batch_no": "బ్యాచ్ నంబర్",
        "btn_confirm": "నిర్ధారించు", "btn_correct": "సరిచేయి",
        "agent_help": "ఒక కేంద్రం ప్రమాదాన్ని వివరించగలను ('MH-0000221 లో ఓఆర్ఎస్ ప్రమాదం ఎందుకు?'), కొరత ఉన్న కేంద్రాలను చెప్పగలను ('ఏ కేంద్రాలు ప్రమాదంలో ఉన్నాయి?'), లేదా బదిలీల ప్రతిపాదనలు తయారు చేయగలను ('బదిలీలు ప్రతిపాదించు'). నేను దేనినీ ఆమోదించలేను లేదా పంపలేను.",
        "agent_explain": "{facility} లో వచ్చే వారం {drug} అయిపోయే అవకాశం {prob}, అంచనా డిమాండ్ సుమారు {p50} యూనిట్లు (పరిధి {p10}-{p90}).",
        "agent_no_forecast": "{facility} లో {drug} అంచనా ఇంకా అందుబాటులో లేదు.",
        "agent_stock": "{facility} తాజా నిల్వ: {lines}.",
        "agent_no_reports": "ఇంకా నివేదికలు లేవు",
        "agent_drafted": "{district} కోసం {n} బదిలీ ప్రతిపాదనలు తయారయ్యాయి. ఆర్డర్ల పేజీలో అధికారి ఆమోదం అవసరం. ఉదాహరణ: {src} నుండి {dst} కు {qty} {drug} ({minutes} నిమిషాలు).",
        "agent_no_transfers": "{district} లో ప్రస్తుతం సాధ్యమయ్యే బదిలీలు లేవు.",
        "agent_at_risk": "{district} లో అత్యధిక ప్రమాదం: {lines}.",
        "agent_at_risk_line": "{name} ({facility}) {drug}: నిల్వ {on_hand}, డిమాండ్ {demand}/వారం",
        "agent_none_at_risk": "{district} లో ఏ కేంద్రంలోనూ నిల్వ ఒక వారం కంటే తక్కువ లేదు.",
        "agent_outside": "ఇది మీ అధికార పరిధికి వెలుపల ఉంది: {detail}",
    },
    "kn": {
        "not_registered": "ಈ ಸಂಖ್ಯೆ ಯಾವುದೇ ಆರೋಗ್ಯ ಕೇಂದ್ರಕ್ಕೆ ನೋಂದಾಯಿಸಲಾಗಿಲ್ಲ.",
        "recorded": "{facility}ಗಾಗಿ ದಾಖಲಿಸಲಾಗಿದೆ: {items}.",
        "unreadable": "ಇದನ್ನು ಓದಲಾಗಲಿಲ್ಲ. ದಾಸ್ತಾನನ್ನು '<ಔಷಧ> <ಪ್ರಮಾಣ>' ರೂಪದಲ್ಲಿ, ಪ್ರತಿ ಸಾಲಿಗೆ ಒಂದು ಕಳುಹಿಸಿ, ಉದಾ. 'ಒಆರ್‌ಎಸ್ 50'. ಅಥವಾ ರಿಜಿಸ್ಟರ್‌ನ ಫೋಟೋ ಕಳುಹಿಸಿ.",
        "confirmed_n": "{n} ದಾಖಲೆ(ಗಳು) ದೃಢೀಕರಿಸಲಾಗಿದೆ.",
        "nothing_pending": "ದೃಢೀಕರಣಕ್ಕೆ ಯಾವುದೂ ಬಾಕಿ ಇಲ್ಲ.",
        "card": "ದಯವಿಟ್ಟು {drug} ದೃಢೀಕರಿಸಿ: {fields} ಬಗ್ಗೆ ನಮಗೆ ಪೂರ್ಣ ಖಚಿತತೆ ಇಲ್ಲ. ಓದಿದಂತೆ ದೃಢೀಕರಿಸಲು ಹೌದು ಎಂದು ಉತ್ತರಿಸಿ, ಅಥವಾ ಸರಿಯಾದ ಮೌಲ್ಯವನ್ನು ಕಳುಹಿಸಿ.",
        "field_drug_id": "ಯಾವ ಔಷಧ", "field_on_hand": "ಪ್ರಮಾಣ",
        "field_expiry": "ಅವಧಿ ಮುಗಿಯುವ ದಿನಾಂಕ", "field_batch_no": "ಬ್ಯಾಚ್ ಸಂಖ್ಯೆ",
        "btn_confirm": "ದೃಢೀಕರಿಸಿ", "btn_correct": "ಸರಿಪಡಿಸಿ",
        "agent_help": "ಒಂದು ಕೇಂದ್ರದ ಅಪಾಯವನ್ನು ವಿವರಿಸಬಲ್ಲೆ ('MH-0000221 ರಲ್ಲಿ ಒಆರ್‌ಎಸ್ ಅಪಾಯ ಏಕೆ?'), ಕೊರತೆಯಿರುವ ಕೇಂದ್ರಗಳನ್ನು ಪಟ್ಟಿ ಮಾಡಬಲ್ಲೆ ('ಯಾವ ಕೇಂದ್ರಗಳು ಅಪಾಯದಲ್ಲಿವೆ?'), ಅಥವಾ ವರ್ಗಾವಣೆ ಪ್ರಸ್ತಾವಗಳನ್ನು ತಯಾರಿಸಬಲ್ಲೆ ('ವರ್ಗಾವಣೆ ಪ್ರಸ್ತಾವಿಸಿ'). ನಾನು ಯಾವುದನ್ನೂ ಅನುಮೋದಿಸಲು ಅಥವಾ ಕಳುಹಿಸಲು ಸಾಧ್ಯವಿಲ್ಲ.",
        "agent_explain": "{facility} ನಲ್ಲಿ ಮುಂದಿನ ವಾರ {drug} ಖಾಲಿಯಾಗುವ ಸಾಧ್ಯತೆ {prob}, ನಿರೀಕ್ಷಿತ ಬೇಡಿಕೆ ಸುಮಾರು {p50} ಘಟಕಗಳು (ವ್ಯಾಪ್ತಿ {p10}-{p90}).",
        "agent_no_forecast": "{facility} ನಲ್ಲಿ {drug}ಗೆ ಮುನ್ಸೂಚನೆ ಇನ್ನೂ ಲಭ್ಯವಿಲ್ಲ.",
        "agent_stock": "{facility} ನ ಇತ್ತೀಚಿನ ದಾಸ್ತಾನು: {lines}.",
        "agent_no_reports": "ಇನ್ನೂ ವರದಿಗಳಿಲ್ಲ",
        "agent_drafted": "{district}ಗಾಗಿ {n} ವರ್ಗಾವಣೆ ಪ್ರಸ್ತಾವಗಳನ್ನು ತಯಾರಿಸಲಾಗಿದೆ. ಆರ್ಡರ್‌ಗಳ ಪುಟದಲ್ಲಿ ಅಧಿಕಾರಿಯ ಅನುಮೋದನೆ ಬೇಕು. ಉದಾಹರಣೆ: {src} ಇಂದ {dst}ಗೆ {qty} {drug} ({minutes} ನಿಮಿಷ).",
        "agent_no_transfers": "{district} ನಲ್ಲಿ ಸದ್ಯ ಯಾವುದೇ ಸಾಧ್ಯ ವರ್ಗಾವಣೆ ಇಲ್ಲ.",
        "agent_at_risk": "{district} ನಲ್ಲಿ ಹೆಚ್ಚು ಅಪಾಯ: {lines}.",
        "agent_at_risk_line": "{name} ({facility}) {drug}: ದಾಸ್ತಾನು {on_hand}, ಬೇಡಿಕೆ {demand}/ವಾರ",
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
