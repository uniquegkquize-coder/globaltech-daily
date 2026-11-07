"""Regional official source pages; domains are sourced, never guessed per district.

The state/UT directory scan complements these immediately usable starting pages.
Shared state portals are intentionally limited to their housing department path.
"""

# Sources: gbnagar.nic.in/public-utility-category/authority/ and the authorities' sites.
# Punjab: punjab.gov.in/government/departments/department-of-housing-and-urban-development/
# Rajasthan: lsg.urban.rajasthan.gov.in/content/raj/udh/udh-department/en/DA-UIT.html
REGIONAL_BOARDS = {
 'UP': (
  'https://www.noidaauthority.in/', 'https://www.greaternoidaauthority.in/',
  'https://yamunaexpresswayauthority.com/index', 'https://upsida.in/',
  'https://sidajaunpur.com/',
  'https://mvdamirzapur.com/', 'https://mdamoradabad.up.gov.in/',
  'https://mdamuzaffarnagar.com/',
 ),
 'PB': (
  'https://www.puda.gov.in/', 'https://gmada.gov.in/en', 'https://glada.gov.in/en',
  'https://jda.gov.in/en', 'https://bdabathinda.in/en', 'https://pdapatiala.in/',
  'https://adaamritsar.gov.in/en',
 ),
 'RJ': (
  'https://jda.rajasthan.gov.in/', 'https://ada.rajasthan.gov.in/',
  'https://bhda.rajasthan.gov.in/', 'https://bda.rajasthan.gov.in/',
  'https://joda.rajasthan.gov.in/', 'https://uda.rajasthan.gov.in/',
  'https://kda.rajasthan.gov.in/',
  'https://uit.rajasthan.gov.in/uitabu', 'https://uit.rajasthan.gov.in/uitalwar',
  'https://uit.rajasthan.gov.in/uitbarmer', 'https://uit.rajasthan.gov.in/uitbhilwara',
  'https://uit.rajasthan.gov.in/uitchittorgarh', 'https://uit.rajasthan.gov.in/uitjaisalmer',
  'https://uit.rajasthan.gov.in/uitpali', 'https://uit.rajasthan.gov.in/uitsawaimadhopur',
  'https://uit.rajasthan.gov.in/uitsikar', 'https://uit.rajasthan.gov.in/uitsriganganagar',
  'https://uit.rajasthan.gov.in/uitdausabandikui', 'https://uit.rajasthan.gov.in/uitbalotra',
 ),
 # Official board/department sites and state government directories.
 'BR': ('https://bshb.bihar.gov.in/',),
 'CG': ('https://www.cghb.gov.in/',),
 'JH': ('https://jshb.jharkhand.gov.in/Home/Index',),
 'GJ': ('https://www.gujarathousingboard.gujarat.gov.in/',),
 'MP': ('https://www.mphousing.in/', 'https://www.idaindore.org/'),
 'MH': ('https://www.mmrda.maharashtra.gov.in/en', 'https://www.pmrda.gov.in/en/home/',
        'https://www.nmrda.org/', 'https://www.nitnagpur.org/',
        'https://housing.maharashtra.gov.in/en/'),
 'KA': ('https://khb.karnataka.gov.in/', 'https://bdakarnataka.in/'),
 'KL': ('https://kshb.kerala.gov.in/',),
 'AP': ('https://housing.apcfss.in/', 'https://crda.ap.gov.in/apcrdav2/views/TeluguHome.aspx'),
 'TS': ('https://tghb.telangana.gov.in/', 'https://www.hmda.gov.in/'),
 'OD': ('https://oshb.org/',),
 'GA': ('https://ghb.goa.gov.in/', 'https://ghb.goa.gov.in/orders-notification-and-circulars/'),
 'AS': ('https://ashb.assam.gov.in/', 'https://gmda.assam.gov.in/'),
 'HP': ('https://www.himuda.hp.gov.in/',),
 'UK': ('https://uhuda.uk.gov.in/', 'https://mddaonline.in/index.php/category/news-updates/'),
 'WB': ('https://www.wbhb.in/', 'https://wbhousingboard.in/', 'https://housing.wb.gov.in/'),
 'CH': ('https://chbonline.in/',),
 'JK': ('https://jkhousingboard.jk.gov.in/',),
 'PY': ('https://tcpd.py.gov.in/PMAY-Notifications',),
 'AR': ('https://www.udarunachal.gov.in/',),
 'ML': ('https://megurban.gov.in/', 'https://www.megurban.gov.in/notification.html',
        'https://mudashillong.org.in/index.html', 'https://mudashillong.gov.in/'),
 'MN': ('https://mahud.mn.gov.in/', 'https://tpmanipur.mn.gov.in/en/notifications/'),
 'MZ': ('https://udpa.mizoram.gov.in/posts',),
 'NL': ('https://ud.nagaland.gov.in/', 'https://npwd.nagaland.gov.in/housing/'),
 'SK': ('https://udd.sikkim.gov.in/visitors/plans',),
 'TR': ('https://tuda.tripura.ind.in/',),
 'LA': ('https://ladakh.gov.in/housing-and-urban-development/',),
}

# Official IGOD state/UT codes. These are directory endpoints, not claims that
# each jurisdiction has a separate housing board or district authority.
STATE_UT_CODES = tuple('AN AP AR AS BR CH CG DN DL GA GJ HR HP JK JH KA KL LA LD MP MH MN ML MZ NL OD PY PB RJ SK TN TS TR UP UK WB'.split())
NATIONAL_CATALOGS = (
 'https://igod.gov.in/sg/states',
 'https://igod.gov.in/sector/FRNsIHQBsvhI6u6Q3tju/organizations',
 'https://igod.gov.in/sector/DRNsIHQBsvhI6u6Q3tju/organizations',
 'https://punjab.gov.in/government/departments/department-of-housing-and-urban-development/',
 'https://uhuda.uk.gov.in/',
) + tuple('https://igod.gov.in/sg/' + code + '/' + section
          for code in STATE_UT_CODES
          for section in ('categories', 'E011/organizations', 'E051/organizations', 'E003/organizations'))

SCOPED_HOSTS = {
 'ladakh.gov.in': ('/housing-and-urban-development/',),
 'npwd.nagaland.gov.in': ('/housing/',),
}
