import CarrierSwitch from "./CarrierDropdown";

function Home() {
    return (
        <div className="App">
      <head>
        <title>Home - CS219</title>
      </head>
      <body>


    <h1>CS219: Cloud Computing</h1>
    <h1>Project: Cloud-Based IoT Management with SIM Card</h1>

    <CarrierSwitch/>


    <h3><u>Downstream Task on IoT Data:</u> View livestream visualization of IoT Data</h3>
    In order to visualize the livestream of IoT Data, we utilize Grafana. <a href="http://localhost:8000/grafana">Click here to go to Grafana.</a>

    <br/>
    <br/>
    <br/>

    <footer>
      <h3>Acknowledgements</h3>
      <p>Developers: Harrison (<a href="mailto:harrison.cassar@gmail.com">harrison.cassar@gmail.com</a>), Ricky (<a href="mailto:harrison.cassar@gmail.com">harrison.cassar@gmail.com</a>), Disha (<a href="mailto:harrison.cassar@gmail.com">harrison.cassar@gmail.com</a>), and Albert (<a href="mailto:harrison.cassar@gmail.com">harrison.cassar@gmail.com</a>)</p>
      <p>Developed as a part of UCLA's Spring 2023 COM SCI 219: Cloud Computing course.</p>
      <p>Special thanks to Mentor Jinghao Zhao and Professor Songwu Lu for guidance throughout the project development process. </p>
    </footer>
  </body>
		  </div>
    );
}

export default Home;