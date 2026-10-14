<div align="center">

{{ block.header }}

{{ block.languages }}

**{{ t.connect }}**

<a href="{{ links.linkedin }}"><img src="https://skillicons.dev/icons?i=linkedin" height="40" alt="LinkedIn"/></a>
<a href="{{ links.instagram }}"><img src="https://skillicons.dev/icons?i=instagram" height="40" alt="Instagram"/></a>
<a href="{{ links.website }}{{ t.website_path }}"><img src="assets/logo.png" height="40" alt="Portfolio"/></a>

<sub><code>{{ motto }}</code></sub>

</div>

---

### {{ t.about.title }}

{{ t.about.body }}

<details>
<summary><b>🔧 {{ t.now.title }} · 📈 {{ t.next.title }}</b></summary>

<table>
<tr>
<td width="50%" valign="top">

**🔧 {{ t.now.title }}**

{{ t.now.items }}

</td>
<td width="50%" valign="top">

**📈 {{ t.next.title }}**

{{ t.next.items }}

</td>
</tr>
</table>

</details>

<details>
<summary><b>⭐ {{ t.featured.title }}</b></summary>

<a href="https://github.com/{{ github_user }}/{{ featured.repo }}"><img src="https://github-readme-stats.vercel.app/api/pin/?username={{ github_user }}&repo={{ featured.repo }}&theme=github_dark&hide_border=true&locale={{ lang.stats_locale }}" alt="{{ featured.repo }}"/></a>

{{ t.featured.body }}

<sub><code>{{ featured.pipeline }}</code></sub>

</details>

<details>
<summary><b>📂 {{ t.projects.title }}</b></summary>

{{ block.projects }}

</details>

<details>
<summary><b>🧰 {{ t.stack.title }}</b></summary>

<sub>{{ t.stack.backend }}</sub><br/>
{{ block.stack.backend }}

<sub>{{ t.stack.data }}</sub><br/>
{{ block.stack.data }}

<sub>{{ t.stack.frontend }}</sub><br/>
{{ block.stack.frontend }}

</details>

<details open>
<summary><b>📊 {{ t.activity.title }}</b></summary>

<div align="center">
<img src="https://raw.githubusercontent.com/andreasbm/readme/master/assets/lines/rainbow.png" width="100%" alt=""/>
<br/><br/>
<img src="https://github-readme-stats.vercel.app/api?username={{ github_user }}&show_icons=true&theme=tokyonight&hide_border=true&bg_color=0D1117&include_all_commits=true&locale={{ lang.stats_locale }}" alt="GitHub stats" width="49%"/>
<img src="https://github-readme-streak-stats.herokuapp.com/?user={{ github_user }}&theme=tokyonight&hide_border=true&background=0D1117&locale={{ lang.stats_locale }}" alt="GitHub streak" width="49%"/>
<br/><br/>
<img src="https://github-readme-stats.vercel.app/api/top-langs/?username={{ github_user }}&layout=compact&langs_count=8&theme=tokyonight&hide_border=true&bg_color=0D1117&locale={{ lang.stats_locale }}" alt="Top languages" width="50%"/>
<br/><br/>
<img src="https://raw.githubusercontent.com/andreasbm/readme/master/assets/lines/rainbow.png" width="100%" alt=""/>
</div>

</details>

---

<div align="center">
<sub>{{ t.footer }}</sub>
</div>

<img src="https://capsule-render.vercel.app/api?type=waving&color={{ header.footer_gradient }}&height=100&section=footer" width="100%" alt=""/>
