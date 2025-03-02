const login = document.getElementById('login')
const register = document.getElementById('register')
const indicator = document.getElementById('indicator')

function updateIndicator(element) {
	const elementRect = element.getBoundingClientRect()
	indicator.style.width = `${element.offsetWidth}px`
	indicator.style.left = `${
		elementRect.left - element.parentElement.getBoundingClientRect().left
	}px`
}

const activeElement = window.location.href.includes('login') ? login : register

updateIndicator(activeElement)

login.addEventListener('click', function () {
	updateIndicator(login)
})

register.addEventListener('click', function () {
	updateIndicator(register)
})
