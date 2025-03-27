document.addEventListener('DOMContentLoaded', function () {
	const login = document.getElementById('login')
	const register = document.getElementById('register')
	const indicator = document.getElementById('indicator')
	const authOptions = document.querySelector('.auth-options')

	function updateIndicator(element) {
		if (!element || !indicator) return

		// Получаем позицию элемента относительно родителя
		const elementRect = element.getBoundingClientRect()
		const parentRect = authOptions.getBoundingClientRect()

		// Устанавливаем ширину и позицию индикатора
		indicator.style.width = `${element.offsetWidth}px`
		indicator.style.left = `${elementRect.left - parentRect.left}px`
	}

	function setActiveTab(element) {
		// Удаляем класс active у всех вкладок
		;[login, register].forEach(tab => {
			tab.classList.remove('active')
		})

		// Добавляем класс active текущей вкладке
		element.classList.add('active')

		// Обновляем позицию индикатора
		updateIndicator(element)
	}

	// Инициализация при загрузке
	const initialActiveTab = window.location.pathname.includes('register')
		? register
		: login
	setActiveTab(initialActiveTab)

	if (login) {
		login.addEventListener('click', function (e) {
			if (e.target.tagName === 'A') return
			setActiveTab(login)
		})
	}

	if (register) {
		register.addEventListener('click', function (e) {
			if (e.target.tagName === 'A') return
			setActiveTab(register)
		})
	}

	window.addEventListener('resize', function () {
		const activeTab = document.querySelector('.auth-options .option.active')
		if (activeTab) updateIndicator(activeTab)
	})
})
