import * as React from "react";
import * as $ from "jquery";
import {Visibility} from "../interfaces";


interface VisibilityDropdownProps extends React.ClassAttributes<PrivacyDropdown> {
	initial: Visibility;
	shortid: string;
}

interface VisibilityDropdownState {
	selected?: Visibility;
	previous?: Visibility;
	working?: boolean;
}

export default class PrivacyDropdown extends React.Component<VisibilityDropdownProps, VisibilityDropdownState> {

	constructor(props: VisibilityDropdownProps, context: any) {
		super(props, context);
		this.state = {
			selected: props.initial,
			previous: props.initial,
			working: false,
		};
	}

	render(): JSX.Element {
		let options = {
			"Public": Visibility.Public,
			"Unlisted": Visibility.Unlisted,
		};

		return <select
			onChange={(e: any) => {
				if (this.state.working) {
					return;
				}
				let selected = e.target.value;
				this.setState({
					selected: selected,
					working: true,
				});
				$.ajax("/api/v1/games/" + this.props.shortid + "/", {
					method: "PATCH",
					dataType: "json",
					data: {visibility: selected},
				})
				.done(() => this.setState({previous: this.state.selected}))
				.fail((x) => {
					let error = "Could not change replay visibility.";
					if(x.responseText) {
						try {
							let response = JSON.parse(x.responseText);
							error += "\n\n" + response.detail;
						}
						catch(e) {
						}
					}
					alert(error);
					this.setState({selected: this.state.previous});
				})
				.always(() => this.setState({working: false}));
			}}
			value={"" + (+this.state.selected)}
			disabled={this.state.working}
		>{$.map(options, (value: Visibility, key: string) => {
			return <option value={"" + (+value)}>{key}</option>;
		})}</select>;
	}
}
