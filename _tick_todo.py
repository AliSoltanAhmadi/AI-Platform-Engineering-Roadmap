with open('TODO.md','r',encoding='utf-8') as f: content=f.read()
for k,v in {
    '### T001 — راه‌انداز واقعی `learn start`':'### T001 — راه‌انداز واقعی `learn start` (DONE)',
    '### T002 — یکپارچه‌سازی جریان اجرای تمرین':'### T002 — یکپارچه‌سازی جریان اجرای تمرین (DONE)',
    '### T003 — ترمیم زیرساخت تست':'### T003 — ترمیم زیرساخت تست (DONE)',
    '### T004 — امتیازدهی امن و قابل‌اعتماد':'### T004 — امتیازدهی امن و قابل‌اعتماد (DONE)',
    '### T005 — حلقه آموزشی feedback و retry':'### T005 — حلقه آموزشی feedback و retry (DONE)',
    '### T006 — مدل پیشرفت واقعی و سازگار':'### T006 — مدل پیشرفت واقعی و سازگار (DONE)',
    '### T007 — ادامه مسیر و منوی مرکزی':'### T007 — ادامه مسیر و منوی مرکزی (DONE)',
}.items():
    content = content.replace(k,v)
with open('TODO.md','w',encoding='utf-8') as f: f.write(content)
print('ticked T001-T006 in TODO.md')
