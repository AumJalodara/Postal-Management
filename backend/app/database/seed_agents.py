"""Default State-wise Delivery Agents seed data covering all 36 States & UTs.
PIN codes and Hub offices are sourced from the Department of Posts postal dataset.
"""

STATE_AGENTS_DATA = [
    # Core reference agents
    {
        "state": "Tamil Nadu",
        "name": "Ramesh Delivery Agent",
        "email": "agent.chennai@postal.gov.in",
        "phone": "9876500002",
        "pin": "600001",
        "hub": "Chennai GPO"
    },
    {
        "state": "Delhi",
        "name": "Suresh Delivery Agent",
        "email": "agent.delhi@postal.gov.in",
        "phone": "9876500003",
        "pin": "110001",
        "hub": "New Delhi GPO"
    },
    {
        "state": "Maharashtra",
        "name": "Mahesh Delivery Agent",
        "email": "agent.mumbai@postal.gov.in",
        "phone": "9876500004",
        "pin": "400001",
        "hub": "Mumbai GPO"
    },
    # Pan-India 33 additional States and Union Territories
    {
        "state": "Andaman and Nicobar Islands",
        "name": "Rajesh Kumar",
        "email": "agent.andaman@postal.gov.in",
        "phone": "9876500005",
        "pin": "744101",
        "hub": "Port Blair H.O"
    },
    {
        "state": "Andhra Pradesh",
        "name": "Venkatesh Rao",
        "email": "agent.andhra@postal.gov.in",
        "phone": "9876500006",
        "pin": "518301",
        "hub": "Adoni H.O (Kurnool)"
    },
    {
        "state": "Arunachal Pradesh",
        "name": "Tashi Norbu",
        "email": "agent.arunachal@postal.gov.in",
        "phone": "9876500007",
        "pin": "791111",
        "hub": "Itanagar H.O"
    },
    {
        "state": "Assam",
        "name": "Pranab Saikia",
        "email": "agent.assam@postal.gov.in",
        "phone": "9876500008",
        "pin": "786001",
        "hub": "Dibrugarh H.O"
    },
    {
        "state": "Bihar",
        "name": "Amit Kumar",
        "email": "agent.bihar@postal.gov.in",
        "phone": "9876500009",
        "pin": "800020",
        "hub": "Lohia Nagar H.O (Patna)"
    },
    {
        "state": "Chandigarh",
        "name": "Harpreet Singh",
        "email": "agent.chandigarh@postal.gov.in",
        "phone": "9876500010",
        "pin": "160017",
        "hub": "Chandigarh GPO"
    },
    {
        "state": "Chhattisgarh",
        "name": "Devendra Sahu",
        "email": "agent.chhattisgarh@postal.gov.in",
        "phone": "9876500011",
        "pin": "494334",
        "hub": "Kanker H.O (Raipur)"
    },
    {
        "state": "Goa",
        "name": "Anthony Fernandes",
        "email": "agent.goa@postal.gov.in",
        "phone": "9876500012",
        "pin": "403601",
        "hub": "Margao H.O"
    },
    {
        "state": "Gujarat",
        "name": "Jignesh Patel",
        "email": "agent.gujarat@postal.gov.in",
        "phone": "9876500013",
        "pin": "380001",
        "hub": "Ahmedabad GPO"
    },
    {
        "state": "Haryana",
        "name": "Vikram Malik",
        "email": "agent.haryana@postal.gov.in",
        "phone": "9876500014",
        "pin": "134003",
        "hub": "Ambala City H.O"
    },
    {
        "state": "Himachal Pradesh",
        "name": "Rohit Thakur",
        "email": "agent.himachal@postal.gov.in",
        "phone": "9876500015",
        "pin": "176061",
        "hub": "Palampur H.O (Kangra)"
    },
    {
        "state": "Jammu and Kashmir",
        "name": "Tariq Bhat",
        "email": "agent.jk@postal.gov.in",
        "phone": "9876500016",
        "pin": "182101",
        "hub": "Udhampur H.O"
    },
    {
        "state": "Jharkhand",
        "name": "Manoj Mahto",
        "email": "agent.jharkhand@postal.gov.in",
        "phone": "9876500017",
        "pin": "829122",
        "hub": "Ramgarh Cantt H.O"
    },
    {
        "state": "Karnataka",
        "name": "Kiran Gowda",
        "email": "agent.karnataka@postal.gov.in",
        "phone": "9876500018",
        "pin": "560004",
        "hub": "Basavanagudi H.O (Bengaluru)"
    },
    {
        "state": "Kerala",
        "name": "Arun Pillai",
        "email": "agent.kerala@postal.gov.in",
        "phone": "9876500019",
        "pin": "688001",
        "hub": "Alappuzha H.O"
    },
    {
        "state": "Ladakh",
        "name": "Stanzin Dorje",
        "email": "agent.ladakh@postal.gov.in",
        "phone": "9876500020",
        "pin": "194101",
        "hub": "Leh H.O"
    },
    {
        "state": "Lakshadweep",
        "name": "Mohammed Koya",
        "email": "agent.lakshadweep@postal.gov.in",
        "phone": "9876500021",
        "pin": "682555",
        "hub": "Kavaratti H.O"
    },
    {
        "state": "Madhya Pradesh",
        "name": "Shivendra Chouhan",
        "email": "agent.mp@postal.gov.in",
        "phone": "9876500022",
        "pin": "472001",
        "hub": "Tikamgarh H.O (Bhopal Circle)"
    },
    {
        "state": "Manipur",
        "name": "Biren Singh",
        "email": "agent.manipur@postal.gov.in",
        "phone": "9876500023",
        "pin": "795001",
        "hub": "Imphal H.O"
    },
    {
        "state": "Meghalaya",
        "name": "Daphishisha Marwein",
        "email": "agent.meghalaya@postal.gov.in",
        "phone": "9876500024",
        "pin": "793001",
        "hub": "Shillong GPO"
    },
    {
        "state": "Mizoram",
        "name": "Lalremruata",
        "email": "agent.mizoram@postal.gov.in",
        "phone": "9876500025",
        "pin": "796001",
        "hub": "Aizawl H.O"
    },
    {
        "state": "Nagaland",
        "name": "Kevichusa Angami",
        "email": "agent.nagaland@postal.gov.in",
        "phone": "9876500026",
        "pin": "797001",
        "hub": "Kohima H.O"
    },
    {
        "state": "Odisha",
        "name": "Subrat Mohanty",
        "email": "agent.odisha@postal.gov.in",
        "phone": "9876500027",
        "pin": "756032",
        "hub": "Jaleswar H.O (Baleshwar)"
    },
    {
        "state": "Puducherry",
        "name": "Saravanan",
        "email": "agent.puducherry@postal.gov.in",
        "phone": "9876500028",
        "pin": "605001",
        "hub": "Pondicherry H.O"
    },
    {
        "state": "Punjab",
        "name": "Gurpreet Singh",
        "email": "agent.punjab@postal.gov.in",
        "phone": "9876500029",
        "pin": "141001",
        "hub": "Ludhiana H.O"
    },
    {
        "state": "Rajasthan",
        "name": "Gajendra Rathore",
        "email": "agent.rajasthan@postal.gov.in",
        "phone": "9876500030",
        "pin": "305801",
        "hub": "Madanganj Kishangarh H.O (Ajmer)"
    },
    {
        "state": "Sikkim",
        "name": "Pemba Bhutia",
        "email": "agent.sikkim@postal.gov.in",
        "phone": "9876500031",
        "pin": "737101",
        "hub": "Gangtok H.O"
    },
    {
        "state": "Telangana",
        "name": "Naveen Reddy",
        "email": "agent.telangana@postal.gov.in",
        "phone": "9876500032",
        "pin": "504208",
        "hub": "Mancherial H.O"
    },
    {
        "state": "The Dadra and Nagar Haveli and Daman and Diu",
        "name": "Pradeep Solanki",
        "email": "agent.dnhdd@postal.gov.in",
        "phone": "9876500033",
        "pin": "396210",
        "hub": "Bhimpore (Daman)"
    },
    {
        "state": "Tripura",
        "name": "Debashish Debbarma",
        "email": "agent.tripura@postal.gov.in",
        "phone": "9876500034",
        "pin": "799120",
        "hub": "Radhakishorepur H.O (Gomati)"
    },
    {
        "state": "Uttar Pradesh",
        "name": "Akhilesh Yadav",
        "email": "agent.up@postal.gov.in",
        "phone": "9876500035",
        "pin": "282003",
        "hub": "Agra Fort H.O"
    },
    {
        "state": "Uttarakhand",
        "name": "Harish Rawat",
        "email": "agent.uttarakhand@postal.gov.in",
        "phone": "9876500036",
        "pin": "263645",
        "hub": "Ranikhet H.O (Almora)"
    },
    {
        "state": "West Bengal",
        "name": "Sourav Mukherjee",
        "email": "agent.westbengal@postal.gov.in",
        "phone": "9876500037",
        "pin": "700056",
        "hub": "Belgharia H.O (24 Paraganas)"
    }
]
