"""District names for Madhya Pradesh and Rajasthan, with common alternate spellings."""
MP = {
 "Agar Malwa": ["agar malwa", "agar"], "Alirajpur": ["alirajpur"], "Anuppur": ["anuppur", "anupur"], "Ashoknagar": ["ashoknagar", "ashok nagar"],
 "Balaghat": ["balaghat"], "Barwani": ["barwani", "badwani"], "Betul": ["betul"], "Bhind": ["bhind"], "Bhopal": ["bhopal"],
 "Burhanpur": ["burhanpur"], "Chhatarpur": ["chhatarpur"], "Chhindwara": ["chhindwara"], "Damoh": ["damoh"], "Datia": ["datia"],
 "Dewas": ["dewas"], "Dhar": ["dhar"], "Dindori": ["dindori"], "Guna": ["guna"], "Gwalior": ["gwalior"], "Harda": ["harda"],
 "Narmadapuram": ["narmadapuram", "hoshangabad", "itarsi"], "Indore": ["indore", "mhow"], "Jabalpur": ["jabalpur"], "Jhabua": ["jhabua"],
 "Katni": ["katni"], "Khandwa": ["khandwa", "east nimar"], "Khargone": ["khargone", "west nimar"], "Mandla": ["mandla"],
 "Mandsaur": ["mandsaur", "mandsour", "garoth", "malhargarh", "sitamau", "suwasra", "bhanpura", "shamgarh"], "Morena": ["morena"],
 "Narsinghpur": ["narsinghpur"], "Neemuch": ["neemuch", "nimach", "manasa", "jawad"], "Niwari": ["niwari"], "Panna": ["panna"],
 "Raisen": ["raisen"], "Rajgarh": ["rajgarh"], "Ratlam": ["ratlam", "jaora"], "Rewa": ["rewa"], "Sagar": ["sagar"], "Satna": ["satna"],
 "Sehore": ["sehore"], "Seoni": ["seoni"], "Shahdol": ["shahdol"], "Shajapur": ["shajapur"], "Sheopur": ["sheopur"], "Shivpuri": ["shivpuri"],
 "Sidhi": ["sidhi"], "Singrauli": ["singrauli"], "Tikamgarh": ["tikamgarh"], "Ujjain": ["ujjain", "nagda"], "Umaria": ["umaria"],
 "Vidisha": ["vidisha"], "Maihar": ["maihar"], "Mauganj": ["mauganj"], "Pandhurna": ["pandhurna"],
}
RJ = {
 "Ajmer": ["ajmer", "kishangarh", "beawar"], "Alwar": ["alwar"], "Banswara": ["banswara"], "Baran": ["baran"], "Barmer": ["barmer", "balotra"],
 "Bharatpur": ["bharatpur", "deeg"], "Bhilwara": ["bhilwara"], "Bikaner": ["bikaner"], "Bundi": ["bundi"], "Chittorgarh": ["chittorgarh", "chittaurgarh", "chittor"],
 "Churu": ["churu"], "Dausa": ["dausa"], "Dholpur": ["dholpur", "dhaulpur"], "Dungarpur": ["dungarpur"], "Sri Ganganagar": ["ganganagar", "sri ganganagar", "shri ganganagar"],
 "Hanumangarh": ["hanumangarh"], "Jaipur": ["jaipur"], "Jaisalmer": ["jaisalmer"], "Jalore": ["jalore", "jalor"], "Jhalawar": ["jhalawar"],
 "Jhunjhunu": ["jhunjhunu", "jhunjhunun"], "Jodhpur": ["jodhpur"], "Karauli": ["karauli"], "Kota": ["kota"], "Nagaur": ["nagaur", "didwana"],
 "Pali": ["pali"], "Pratapgarh": ["pratapgarh"], "Rajsamand": ["rajsamand"], "Sawai Madhopur": ["sawai madhopur", "sawaimadhopur"],
 "Sikar": ["sikar"], "Sirohi": ["sirohi", "abu road", "mount abu"], "Tonk": ["tonk"], "Udaipur": ["udaipur"], "Kotputli-Behror": ["kotputli", "behror"],
 "Khairthal-Tijara": ["khairthal", "tijara"], "Phalodi": ["phalodi"], "Salumbar": ["salumbar"],
}
STATE_DISTRICTS = {"Madhya Pradesh": MP, "Rajasthan": RJ}

# Fallback: first 3 digits of the PIN code -> main district (used only when no name matches)
PIN3 = {
 "450": "Khandwa", "451": "Khargone", "452": "Indore", "453": "Indore", "454": "Dhar", "455": "Dewas", "456": "Ujjain",
 "457": "Ratlam", "458": "Mandsaur", "460": "Betul", "461": "Narmadapuram", "462": "Bhopal", "463": "Bhopal", "464": "Vidisha",
 "465": "Shajapur", "466": "Sehore", "470": "Sagar", "471": "Chhatarpur", "472": "Tikamgarh", "473": "Guna", "474": "Gwalior",
 "475": "Gwalior", "476": "Morena", "477": "Bhind", "480": "Chhindwara", "481": "Balaghat", "482": "Jabalpur", "483": "Katni",
 "484": "Shahdol", "485": "Satna", "486": "Rewa", "487": "Narsinghpur", "488": "Panna",
 "301": "Alwar", "302": "Jaipur", "303": "Jaipur", "304": "Tonk", "305": "Ajmer", "306": "Pali", "307": "Sirohi",
 "311": "Bhilwara", "312": "Chittorgarh", "313": "Udaipur", "314": "Dungarpur", "321": "Bharatpur", "322": "Sawai Madhopur",
 "323": "Bundi", "324": "Kota", "325": "Baran", "326": "Jhalawar", "327": "Banswara", "328": "Dholpur", "331": "Churu",
 "332": "Sikar", "333": "Jhunjhunu", "334": "Bikaner", "335": "Sri Ganganagar", "341": "Nagaur", "342": "Jodhpur",
 "343": "Jalore", "344": "Barmer", "345": "Jaisalmer",
}
PIN4 = {"4584": "Neemuch", "4583": "Neemuch", "4574": "Jhabua", "4573": "Ratlam", "4570": "Ratlam", "4581": "Mandsaur", "4580": "Mandsaur"}
