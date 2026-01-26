from resume_parser import parse_resume

text = parse_resume("resume/my_resume.pdf")
print(text[:1000])
