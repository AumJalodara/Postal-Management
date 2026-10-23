// 36 State & Union Territory Delivery Agents from Postal Dataset
export const STATE_AGENTS = [
  // Core reference hubs
  {
    state: 'Tamil Nadu',
    name: 'Ramesh Delivery Agent',
    email: 'agent.chennai@postal.gov.in',
    pin: '600001',
    hub: 'Chennai GPO',
    phone: '9876500002',
    region: 'South'
  },
  {
    state: 'Delhi',
    name: 'Suresh Delivery Agent',
    email: 'agent.delhi@postal.gov.in',
    pin: '110001',
    hub: 'New Delhi GPO',
    phone: '9876500003',
    region: 'North'
  },
  {
    state: 'Maharashtra',
    name: 'Mahesh Delivery Agent',
    email: 'agent.mumbai@postal.gov.in',
    pin: '400001',
    hub: 'Mumbai GPO',
    phone: '9876500004',
    region: 'West'
  },
  // Pan-India 33 additional States and Union Territories
  {
    state: 'Andaman and Nicobar Islands',
    name: 'Rajesh Kumar',
    email: 'agent.andaman@postal.gov.in',
    pin: '744101',
    hub: 'Port Blair H.O',
    phone: '9876500005',
    region: 'Islands'
  },
  {
    state: 'Andhra Pradesh',
    name: 'Venkatesh Rao',
    email: 'agent.andhra@postal.gov.in',
    pin: '518301',
    hub: 'Adoni H.O (Kurnool)',
    phone: '9876500006',
    region: 'South'
  },
  {
    state: 'Arunachal Pradesh',
    name: 'Tashi Norbu',
    email: 'agent.arunachal@postal.gov.in',
    pin: '791111',
    hub: 'Itanagar H.O',
    phone: '9876500007',
    region: 'North-East'
  },
  {
    state: 'Assam',
    name: 'Pranab Saikia',
    email: 'agent.assam@postal.gov.in',
    pin: '786001',
    hub: 'Dibrugarh H.O',
    phone: '9876500008',
    region: 'North-East'
  },
  {
    state: 'Bihar',
    name: 'Amit Kumar',
    email: 'agent.bihar@postal.gov.in',
    pin: '800020',
    hub: 'Lohia Nagar H.O (Patna)',
    phone: '9876500009',
    region: 'East'
  },
  {
    state: 'Chandigarh',
    name: 'Harpreet Singh',
    email: 'agent.chandigarh@postal.gov.in',
    pin: '160017',
    hub: 'Chandigarh GPO',
    phone: '9876500010',
    region: 'North'
  },
  {
    state: 'Chhattisgarh',
    name: 'Devendra Sahu',
    email: 'agent.chhattisgarh@postal.gov.in',
    pin: '494334',
    hub: 'Kanker H.O (Raipur)',
    phone: '9876500011',
    region: 'Central'
  },
  {
    state: 'Goa',
    name: 'Anthony Fernandes',
    email: 'agent.goa@postal.gov.in',
    pin: '403601',
    hub: 'Margao H.O',
    phone: '9876500012',
    region: 'West'
  },
  {
    state: 'Gujarat',
    name: 'Jignesh Patel',
    email: 'agent.gujarat@postal.gov.in',
    pin: '382721',
    hub: 'Kalol H.O (Gandhinagar)',
    phone: '9876500013',
    region: 'West'
  },
  {
    state: 'Haryana',
    name: 'Vikram Malik',
    email: 'agent.haryana@postal.gov.in',
    pin: '134003',
    hub: 'Ambala City H.O',
    phone: '9876500014',
    region: 'North'
  },
  {
    state: 'Himachal Pradesh',
    name: 'Rohit Thakur',
    email: 'agent.himachal@postal.gov.in',
    pin: '176061',
    hub: 'Palampur H.O (Kangra)',
    phone: '9876500015',
    region: 'North'
  },
  {
    state: 'Jammu and Kashmir',
    name: 'Tariq Bhat',
    email: 'agent.jk@postal.gov.in',
    pin: '182101',
    hub: 'Udhampur H.O',
    phone: '9876500016',
    region: 'North'
  },
  {
    state: 'Jharkhand',
    name: 'Manoj Mahto',
    email: 'agent.jharkhand@postal.gov.in',
    pin: '829122',
    hub: 'Ramgarh Cantt H.O',
    phone: '9876500017',
    region: 'East'
  },
  {
    state: 'Karnataka',
    name: 'Kiran Gowda',
    email: 'agent.karnataka@postal.gov.in',
    pin: '560004',
    hub: 'Basavanagudi H.O (Bengaluru)',
    phone: '9876500018',
    region: 'South'
  },
  {
    state: 'Kerala',
    name: 'Arun Pillai',
    email: 'agent.kerala@postal.gov.in',
    pin: '688001',
    hub: 'Alappuzha H.O',
    phone: '9876500019',
    region: 'South'
  },
  {
    state: 'Ladakh',
    name: 'Stanzin Dorje',
    email: 'agent.ladakh@postal.gov.in',
    pin: '194101',
    hub: 'Leh H.O',
    phone: '9876500020',
    region: 'North'
  },
  {
    state: 'Lakshadweep',
    name: 'Mohammed Koya',
    email: 'agent.lakshadweep@postal.gov.in',
    pin: '682555',
    hub: 'Kavaratti H.O',
    phone: '9876500021',
    region: 'Islands'
  },
  {
    state: 'Madhya Pradesh',
    name: 'Shivendra Chouhan',
    email: 'agent.mp@postal.gov.in',
    pin: '472001',
    hub: 'Tikamgarh H.O (Bhopal Circle)',
    phone: '9876500022',
    region: 'Central'
  },
  {
    state: 'Manipur',
    name: 'Biren Singh',
    email: 'agent.manipur@postal.gov.in',
    pin: '795001',
    hub: 'Imphal H.O',
    phone: '9876500023',
    region: 'North-East'
  },
  {
    state: 'Meghalaya',
    name: 'Daphishisha Marwein',
    email: 'agent.meghalaya@postal.gov.in',
    pin: '793001',
    hub: 'Shillong GPO',
    phone: '9876500024',
    region: 'North-East'
  },
  {
    state: 'Mizoram',
    name: 'Lalremruata',
    email: 'agent.mizoram@postal.gov.in',
    pin: '796001',
    hub: 'Aizawl H.O',
    phone: '9876500025',
    region: 'North-East'
  },
  {
    state: 'Nagaland',
    name: 'Kevichusa Angami',
    email: 'agent.nagaland@postal.gov.in',
    pin: '797001',
    hub: 'Kohima H.O',
    phone: '9876500026',
    region: 'North-East'
  },
  {
    state: 'Odisha',
    name: 'Subrat Mohanty',
    email: 'agent.odisha@postal.gov.in',
    pin: '756032',
    hub: 'Jaleswar H.O (Baleshwar)',
    phone: '9876500027',
    region: 'East'
  },
  {
    state: 'Puducherry',
    name: 'Saravanan',
    email: 'agent.puducherry@postal.gov.in',
    pin: '605001',
    hub: 'Pondicherry H.O',
    phone: '9876500028',
    region: 'South'
  },
  {
    state: 'Punjab',
    name: 'Gurpreet Singh',
    email: 'agent.punjab@postal.gov.in',
    pin: '141001',
    hub: 'Ludhiana H.O',
    phone: '9876500029',
    region: 'North'
  },
  {
    state: 'Rajasthan',
    name: 'Gajendra Rathore',
    email: 'agent.rajasthan@postal.gov.in',
    pin: '305801',
    hub: 'Madanganj Kishangarh H.O (Ajmer)',
    phone: '9876500030',
    region: 'North'
  },
  {
    state: 'Sikkim',
    name: 'Pemba Bhutia',
    email: 'agent.sikkim@postal.gov.in',
    pin: '737101',
    hub: 'Gangtok H.O',
    phone: '9876500031',
    region: 'North-East'
  },
  {
    state: 'Telangana',
    name: 'Naveen Reddy',
    email: 'agent.telangana@postal.gov.in',
    pin: '504208',
    hub: 'Mancherial H.O',
    phone: '9876500032',
    region: 'South'
  },
  {
    state: 'The Dadra and Nagar Haveli and Daman and Diu',
    name: 'Pradeep Solanki',
    email: 'agent.dnhdd@postal.gov.in',
    pin: '396210',
    hub: 'Bhimpore (Daman)',
    phone: '9876500033',
    region: 'West'
  },
  {
    state: 'Tripura',
    name: 'Debashish Debbarma',
    email: 'agent.tripura@postal.gov.in',
    pin: '799120',
    hub: 'Radhakishorepur H.O (Gomati)',
    phone: '9876500034',
    region: 'North-East'
  },
  {
    state: 'Uttar Pradesh',
    name: 'Akhilesh Yadav',
    email: 'agent.up@postal.gov.in',
    pin: '282003',
    hub: 'Agra Fort H.O',
    phone: '9876500035',
    region: 'North'
  },
  {
    state: 'Uttarakhand',
    name: 'Harish Rawat',
    email: 'agent.uttarakhand@postal.gov.in',
    pin: '263645',
    hub: 'Ranikhet H.O (Almora)',
    phone: '9876500036',
    region: 'North'
  },
  {
    state: 'West Bengal',
    name: 'Sourav Mukherjee',
    email: 'agent.westbengal@postal.gov.in',
    pin: '700056',
    hub: 'Belgharia H.O (24 Paraganas)',
    phone: '9876500037',
    region: 'East'
  }
];

export const getAgentByPin = (pin) => {
  return STATE_AGENTS.find(a => a.pin === pin) || null;
};

export const getAgentByEmail = (email) => {
  return STATE_AGENTS.find(a => a.email.toLowerCase() === email.toLowerCase()) || null;
};
