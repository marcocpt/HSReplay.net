import * as $ from "jquery";


export default class jQueryCSRF {

	/**
	 * Sets up the jQuery Ajax calls to use the CSRF token from django.
	 * Based on https://docs.djangoproject.com/en/1.10/ref/csrf/#ajax
	 */
	public static init(): void {
		let token = this.getCookie("csrftoken");
		console.debug(token);
		$.ajaxSetup({
			beforeSend: function (xhr, settings) {
				if (!(/^(GET|HEAD|OPTIONS|TRACE)$/.test(settings.type)) && !this.crossDomain) {
					xhr.setRequestHeader("X-CSRFToken", token);
				}
			}
		});
	}

	private static getCookie(name: string): string {
		let cookieValue = null;
		if (document.cookie && document.cookie !== "") {
			let cookies = document.cookie.split(";");
			for (let i = 0; i < cookies.length; i++) {
				let cookie = jQuery.trim(cookies[i]);
				// Does this cookie string begin with the name we want?
				if (cookie.substring(0, name.length + 1) === (name + "=")) {
					cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
					break;
				}
			}
		}
		return cookieValue;
	}

}
