<div align="center">

{{ block.header }}

{{ block.languages }}

<a href="{{ links.linkedin }}"><img src="https://img.shields.io/badge/LinkedIn-0A66C2?style=flat-square&logo=linkedin&logoColor=white" alt="LinkedIn"/></a>
<a href="{{ links.instagram }}"><img src="https://img.shields.io/badge/Instagram-E4405F?style=flat-square&logo=instagram&logoColor=white" alt="Instagram"/></a>
<a href="{{ links.website }}{{ t.website_path }}"><img src="https://img.shields.io/badge/{{ t.website_label }}-111827?style=flat-square&logo=vercel&logoColor=white" alt="{{ t.website_label }}"/></a>
{{ block.location_badge }}

<sub><code>{{ motto }}</code></sub>

</div>

---

### {{ t.about.title }}

{{ t.about.body }}

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

### {{ t.featured.title }}

<a href="https://github.com/{{ github_user }}/{{ featured.repo }}"><img src="https://github-readme-stats.vercel.app/api/pin/?username={{ github_user }}&repo={{ featured.repo }}&theme=github_dark&hide_border=true&locale={{ lang.stats_locale }}" alt="{{ featured.repo }}"/></a>

{{ t.featured.body }}

<sub><code>{{ featured.pipeline }}</code></sub>

### {{ t.projects.title }}

{{ block.projects }}

### {{ t.stack.title }}

<sub>{{ t.stack.backend }}</sub><br/>
{{ block.stack.backend }}

<sub>{{ t.stack.data }}</sub><br/>
{{ block.stack.data }}

<sub>{{ t.stack.frontend }}</sub><br/>
{{ block.stack.frontend }}

### {{ t.activity.title }}

<div align="center">
<img height="165" src="https://github-readme-stats.vercel.app/api?username={{ github_user }}&show_icons=true&theme=github_dark&hide_border=true&include_all_commits=true&locale={{ lang.stats_locale }}" alt="GitHub stats"/>
<img height="165" src="https://github-readme-stats.vercel.app/api/top-langs/?username={{ github_user }}&layout=compact&theme=github_dark&hide_border=true&locale={{ lang.stats_locale }}" alt="Top languages"/>
</div>

---

<div align="center">
<sub>{{ t.footer }}</sub>
</div>

<img src="https://capsule-render.vercel.app/api?type=waving&color={{ header.footer_gradient }}&height=100&section=footer" width="100%" alt=""/>
