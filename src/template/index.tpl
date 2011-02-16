<html>
<head><title>TOWNTWIT</title></head>
<body>
<h1>TOWNTWIT</h1>

<p>{{ user.user.nickname }}님, 안녕하세요. </p>
<p>
사용자께서 TOWNTWIT에 동네와 트위터 접근 권한을 주시면 
트위터의 새글(리플라이 멘션이나 리트윗 제외)을 주기적으로
(보통 3분에 한번 꼴로) 체크해서, 동네 학번 게시판으로
옮겨드립니다.
</p>
<p>

</p>

<hr/>

{% if town_user %}
<p><img width=40 height=40 src='{{ town_user.img_url }}'/>
동네 인증 성공 - {{ town_user.name }}({{ town_user.id }})</p>
<p><a href='/towntoken/delete'>동네 인증 취소</a></p>
{% else %} 
<p><a href='/town_auth'>동네 인증하기</a></p>
{% endif %}	

<hr/>

{% if twit_user %}
<p>
<img width=40 height=40 src='{{ twit_user.profile_image_url }}'/>
트위터 인증 성공 - {{ twit_user.name }}({{ twit_user.screen_name }})
</p>
<p><a href='/twittoken/delete'>트위터 인증 취소</a></p>
	{% if last_twit %}
	<p>"{{ last_twit.text }}"
	다음 트윗부터 {{ user.town_board_id }}로 옮깁니다.</p>
	{% endif %}
{% else %} 
<p> <a href='/twit_auth'>트위터 인증하기</a> </p>
{% endif %}	

<hr/>

<p>
<a href='http://towntwit.appspot.com'>TOWNTWIT</a> on 
<a target='_blank' href='http://code.google.com/appengine'>GAE</a>/<a target='_blank' href='http://python.org'>P</a> 
by <a href='mailto:gochist@gmail.com'>이덕준</a>
</p> 

<p>
<p><a href='{{ logout_url }}'>로그아웃</a></p>
</p>
</body>
</html>