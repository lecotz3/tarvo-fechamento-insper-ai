import email, sys, os
from email import policy
p, out = sys.argv[1], sys.argv[2]
msg = email.message_from_file(open(p, encoding='utf-8'), policy=policy.default)
for part in msg.iter_attachments():
    fn = part.get_filename()
    open(os.path.join(out, fn), 'wb').write(part.get_content())
    print('saved', fn)
