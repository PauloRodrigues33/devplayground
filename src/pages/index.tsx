import type { NextPage } from 'next'
import Head from 'next/head'
import { useEffect } from 'react';
import 'swiper/css';
import * as THREE from 'three';

const Home: NextPage = () => {


  const createScene = () => {
    var scene = new THREE.Scene();
    var camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 2000);
    camera.position.z = 5;
    var renderer = new THREE.WebGLRenderer();
    renderer.setSize(window.innerWidth, window.innerHeight);
    document.getElementById('3d')?.appendChild(renderer.domElement);

    var geometry = new THREE.BoxGeometry(1, 1, 1);
    var material = new THREE.MeshBasicMaterial({color: '#f00', opacity: 1});
    var cube = new THREE.Mesh(geometry, material);
    scene.add(cube);

    const Update = () => {
      requestAnimationFrame(Update);
      cube.rotation.x += 0.01;
      cube.rotation.y += 0.01;
      renderer.render(scene, camera);
    }

    Update();
  }

  useEffect(() => {
    createScene();
  }, []);


  return (
    <div>
      <Head>
        <title>Developers Playground</title>
        <meta name="description" content="A open source project to developers test their ideas" />
        <link rel="icon" href="/favicon.ico" />
      </Head>
      <main>
        <div id='3d'></div>
      </main>
    </div>
  )
}

export default Home
