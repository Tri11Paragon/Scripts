#!python3

import argparse
import os
from pathlib import Path
import shutil
import re

latex_imports = r"""
\documentclass[12pt,a4paper]{report}

\usepackage{amsmath}
\usepackage{amsfonts}
\usepackage{svg}
\usepackage{subcaption}
\usepackage{acronym}
\usepackage{algorithm}
\usepackage{algpseudocode}
\usepackage[noadjust]{cite}
\usepackage[section]{placeins}
\usepackage{mathtools}
\usepackage{xcolor}

\usepackage{datetime}
\usepackage{longtable}
\usepackage{tabularx}
\usepackage{graphicx}
\usepackage{xcolor}
\usepackage{tcolorbox}

\usepackage[hyperfootnotes,hidelinks]{hyperref}
\hypersetup{
	linktoc=all
}
"""

latex_commands = r"""
\newcommand{\Var}[1]{\textcolor{blue}{#1}} % Color variables in blue
\renewcommand{\contentsname}{Table of Contents}
"""

cover_begin = "%----------EDIT COVER INFO HERE -----------------%"
cover_end = "%------------------------------------------------%"

latex_main = r"""
\newtcbox{\inlinecode}{on line,
	boxsep=1pt, left=1pt, right=1pt, top=1pt, bottom=1pt,
	colframe=gray!50, colback=gray!20, rounded corners, boxrule=0.5pt}

\newdateformat{monthyeardate}{%
	\monthname[\THEMONTH], \THEYEAR}

\begin{document}
	\setlength{\parindent}{0em}
	\setlength{\parskip}{0.5em}
	
	\pagenumbering{Roman}
	
	
	\begin{titlepage}
		\vfill
		\begin{center}
			\includegraphics[width=0.6\textwidth]{\LOGOPATH} \\
			\fontsize{14pt}{14pt}\selectfont
			\vfill
			\UNIVERSITY \\
			\FACULTY \\
			\DEPARTEMENT \\
			\vfill
			\fontsize{18pt}{18pt}\selectfont
			\textbf{\PROJECTTITLE} \\
			\fontsize{14pt}{14pt}\selectfont
			\COURSE
			\vfill
			\fontsize{16pt}{16pt}\selectfont
			Prepared By: \\
			\fontsize{14pt}{14pt}\selectfont
			\STUDENT \ \#\STUDENTNO \\
			\STUDENTEMAIL \\
			\vfill
			\fontsize{16pt}{16pt}\selectfont
			Instructor: \\
			\fontsize{14pt}{14pt}\selectfont
			\SUPERVISOR
			\vfill
			\vfill
			\vfill
			\monthyeardate\today
		\end{center}
	\end{titlepage}
	
	
	\cleardoublepage \phantomsection \addcontentsline{toc}{chapter}{Table of Contents}
	\tableofcontents
	
	\cleardoublepage
	
	\setlength{\parindent}{0em}
	\setlength{\parskip}{0.5em}
	
	\pagenumbering{arabic}
	
	\include{chapters/writeup}
\end{document}
"""

def generate_vars(args):
    try:
        script_dir = Path(__file__).resolve().parent
    except NameError:
        script_dir = Path.cwd()

    project_path = Path.cwd() / slugify(args.name)
    project_path.mkdir(exist_ok=True, parents=True)
    (project_path / "assets").mkdir(exist_ok=True)
    (project_path / "chapters").mkdir(exist_ok=True)
    os.chdir(project_path)

    if args.logo:
        logo = fr"\def \LOGOPATH {{{args.logo}}}"
    else:
        logo = r"\def \LOGOPATH {assets/brock.jpg}"
        shutil.copy(script_dir / "brock.jpg", "assets/brock.jpg")

    if args.title:
        title = fr"\def \PROJECTTITLE {{{args.title}}}"
    else:
        title = fr"\def \PROJECTTITLE {{{args.name}}}"

    if args.course:
        course = fr"\def \COURSE {{{args.course}}}"
    else:
        course = r"\def \COURSE {}"

    if args.instructor:
        instructor = fr"\def \SUPERVISOR {{{args.instructor}}}"
    else:
        instructor = r"\def \SUPERVISOR {}"

    department = fr"\def \DEPARTEMENT {{{args.department}}}"
    faculty = fr"\def \FACULTY {{{args.faculty}}}"
    student = fr"\def \STUDENT {{{args.student}}}"
    student_id = fr"\def \STUDENTNO {{{args.id}}}"
    student_email = fr"\def \STUDENTEMAIL {{{args.email}}}"
    university = r"\def \UNIVERSITY {Brock University}"

    return "\n".join([logo, title, course, instructor, department, faculty, student, student_id, student_email, university])

def slugify(s: str) -> str:
    s = re.sub(r"\W+", "_", s)
    return re.sub(r"_+", "_", s).strip("_").lower()


def main():
    parser = argparse.ArgumentParser(description="Generate LaTeX Project. Generates a new folder with the name")
    parser.add_argument("-o", "--open", help="Open TexStudio in the generated folder", action="store_true", default=False)
    parser.add_argument("-f", "--faculty", help="Specify the name of the faculty", default="Faculty of Mathematics \\& Science")
    parser.add_argument("-d", "--department", help="Specify the name of the department", default="Department of Computer Science")
    parser.add_argument("-s", "--student", help="Specify the name of the student", default="Brett Terpstra")
    parser.add_argument("-i", "--id", help="Specify the ID of the student", default="6920201")
    parser.add_argument("-e", "--email", help="Specify the email of the student", default="bt19ex@brocku.ca")
    parser.add_argument("-u", "--university", help="Specify the university", default="Brock University")

    parser.add_argument("-t", "--title", help="Specify the title of the project", default=None)
    parser.add_argument("-l", "--logo", help="Specify the logo path", default=None)

    parser.add_argument("name", help="Name of the project. If you do not give a title flag, this will be used as the project name")
    parser.add_argument("instructor", help="Specify the name of the professor")
    parser.add_argument("course", help="Specify the name of the course")

    args = parser.parse_args()

    cover_info = generate_vars(args)

    file_data = "\n".join([latex_imports, latex_commands, cover_begin, cover_info, cover_end, latex_main])

    with open(slugify(args.name) + ".tex", "w") as f:
        f.write(file_data)

    with open("chapters/writeup.tex", "w") as f:
        f.write("")

    if args.open:
        os.system("nohup texstudio --start-always --no-session --master \"" + slugify(args.name) + ".tex\" \"chapters/writeup.tex\" >/dev/null 2>&1 < /dev/null &")


if __name__ == "__main__":
    main()
