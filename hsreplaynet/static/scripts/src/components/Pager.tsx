import * as React from "react";


interface PagerProps extends React.ClassAttributes<Pager> {
	next?: () => void;
	previous?: () => void;
}

export default class Pager extends React.Component<PagerProps, void> {

	render(): JSX.Element {
		return <nav className="btn-group">
			<button
					className="btn btn-default"
				onClick={(e) => {
					this.props.previous && this.props.previous();
				}}
				disabled={!this.props.previous}
			>
				Previous
			</button>
			<button
				className="btn btn-default"
				onClick={(e) => {
					this.props.next && this.props.next();
				}}
				disabled={!this.props.next}
			>
				Next
			</button>
		</nav>;
	}
}
