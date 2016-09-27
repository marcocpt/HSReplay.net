import * as React from "react";
import * as $ from "jquery";
import {Visibility} from "../interfaces";


interface DeleteReplayButtonProps extends React.ClassAttributes<DeleteReplayButton> {
	shortid: string;
	done?: () => void;
}

interface DeleteReplayButtonState {
	working?: boolean;
}

export default class DeleteReplayButton extends React.Component<DeleteReplayButtonProps, DeleteReplayButtonState> {
	constructor(props: DeleteReplayButtonProps, context: any) {
		super(props, context);
		this.state = {
			working: false,
		};
	}

	render(): JSX.Element {
		return <button
			className="btn btn-danger btn-xs"
			disabled={this.state.working}
			onClick={() => {
				if (this.state.working) {
					return;
				}
				if (!confirm("Are you sure you would like to remove this replay?")) {
					return;
				}
				this.setState({working: true});
				$.ajax("/api/v1/games/" + this.props.shortid + "/", {
					method: "DELETE",
					dataType: "json",
				})
				.done(() => this.props.done && this.props.done())
				.fail((x) => {
					let error = "Could not delete replay.";
					if(x.responseText) {
						try {
							let response = JSON.parse(x.responseText);
							error += "\n\n" + response.detail;
						}
						catch(e) {
						}
					}
					alert(error);
					this.setState({working: false});
				});
			}}>
			{this.state.working ? "Deleting…" : "Delete"}
		</button>
	}
}
